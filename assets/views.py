import csv
import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, role_required
from notifications.services import notify_device_assigned

from .forms import AssetAssignForm, AssetForm
from .models import Asset, AssetAssignment


def _hx_toast(level: str, message: str, status: int = 200, extra_events: dict | None = None) -> HttpResponse:
    payload: dict = {
        'toast': {'level': level, 'message': str(message)},
    }
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_list_view(request):
    assets = Asset.objects.select_related('asset_type', 'client', 'homeworker__client').all()

    if request.user.is_client:
        assets = assets.filter(client__user=request.user)

    search = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')

    if search:
        assets = assets.filter(
            Q(asset_tag__icontains=search) |
            Q(asset_type__name__icontains=search) |
            Q(homeworker__name__icontains=search) |
            Q(client__company_name__icontains=search)
        )
    if type_filter:
        assets = assets.filter(asset_type_id=type_filter)
    if status_filter in dict(Asset.Status.choices):
        assets = assets.filter(status=status_filter)

    page_num = request.GET.get('page', 1)
    paginator = Paginator(assets, 50)
    page_obj = paginator.get_page(page_num)

    from masters.models import AssetType
    context = {
        'assets': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'statuses': Asset.Status.choices,
        'asset_types': AssetType.objects.filter(is_active=True),
        'selected_type': type_filter,
        'selected_status': status_filter,
        'search': search,
        'page_title': 'Assets',
    }
    if is_htmx(request):
        return render(request, 'assets/_asset_list_content.html', context)
    return render(request, 'assets/asset_list.html', context)


def _get_filtered_assets(request):
    assets = Asset.objects.select_related('asset_type', 'client', 'homeworker__client').all()
    search = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    if search:
        assets = assets.filter(
            Q(asset_tag__icontains=search) |
            Q(asset_type__name__icontains=search) |
            Q(homeworker__name__icontains=search) |
            Q(client__company_name__icontains=search)
        )
    if type_filter:
        assets = assets.filter(asset_type_id=type_filter)
    if status_filter in dict(Asset.Status.choices):
        assets = assets.filter(status=status_filter)
    return assets


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_export_csv(request):
    assets = _get_filtered_assets(request)
    if request.user.is_client:
        assets = assets.filter(client__user=request.user)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="assets.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Asset Tag', 'Serial Number', 'Type', 'Brand', 'Model',
        'Specifications', 'Purchase Date', 'Purchase Price', 'Warranty Expiry',
        'Status', 'Client', 'Homeworker', 'Location', 'Notes', 'Active',
        'Created At', 'Updated At',
    ])
    for a in assets:
        writer.writerow([
            a.asset_tag,
            a.serial_number,
            a.asset_type.name,
            a.brand,
            a.model_name,
            a.specifications,
            a.purchase_date or '',
            a.purchase_price or '',
            a.warranty_expiry or '',
            a.get_status_display(),
            a.client.company_name if a.client else '',
            a.homeworker.name if a.homeworker else '',
            a.location,
            a.notes,
            'Yes' if a.is_active else 'No',
            a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else '',
            a.updated_at.strftime('%Y-%m-%d %H:%M') if a.updated_at else '',
        ])
    return response


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_create_view(request):
    if request.method == 'POST':
        if request.user.is_client:
            from .forms import ClientAssetForm
            form = ClientAssetForm(request.POST, user=request.user)
        else:
            form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Asset {asset.asset_tag} created.', status=204, extra_events={'asset-saved': True})
            messages.success(request, f'Asset {asset.asset_tag} created successfully.')
            return redirect('assets:asset_list')
    else:
        if request.user.is_client:
            from .forms import ClientAssetForm
            form = ClientAssetForm(user=request.user)
        else:
            form = AssetForm()

    template = 'assets/_asset_form_partial.html' if is_htmx(request) else 'assets/asset_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Asset'})


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_update_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if request.user.is_client and asset.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this asset.')

    if request.method == 'POST':
        if request.user.is_client:
            from .forms import ClientAssetForm
            form = ClientAssetForm(request.POST, instance=asset, user=request.user)
        else:
            form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Asset {asset.asset_tag} updated.', status=204, extra_events={'asset-saved': True})
            messages.success(request, f'Asset {asset.asset_tag} updated successfully.')
            return redirect('assets:asset_list')
    else:
        if request.user.is_client:
            from .forms import ClientAssetForm
            form = ClientAssetForm(instance=asset, user=request.user)
        else:
            form = AssetForm(instance=asset)

    template = 'assets/_asset_form_partial.html' if is_htmx(request) else 'assets/asset_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': asset, 'page_title': f'Edit Asset — {asset.asset_tag}'})


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_delete_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if request.user.is_client and asset.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this asset.')

    if request.method == 'POST':
        tag = asset.asset_tag
        asset.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Asset {tag} deleted.', status=204, extra_events={'asset-saved': True})
        messages.success(request, f'Asset {tag} deleted successfully.')
        return redirect('assets:asset_list')

    template = 'assets/_asset_confirm_delete_partial.html' if is_htmx(request) else 'assets/asset_confirm_delete.html'
    return render(request, template, {'obj': asset, 'page_title': f'Delete Asset — {asset.asset_tag}'})


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_detail_view(request, pk):
    asset = get_object_or_404(
        Asset.objects.select_related('asset_type', 'client', 'homeworker__client'),
        pk=pk
    )

    if request.user.is_client and (not asset.client or asset.client.user != request.user):
        return HttpResponseForbidden('You do not have access to this asset.')

    assignments = asset.assignments.select_related('client', 'homeworker__client', 'assigned_by')[:10]
    return render(request, 'assets/asset_detail.html', {
        'obj': asset,
        'assignments': assignments,
        'page_title': str(asset),
    })


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def asset_assign_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if request.method == 'POST':
        form = AssetAssignForm(request.POST)
        if form.is_valid():
            client = form.cleaned_data['client']
            homeworker = form.cleaned_data['homeworker']
            notes = form.cleaned_data['notes']

            assignment = AssetAssignment.objects.create(
                asset=asset,
                client=client,
                homeworker=homeworker,
                assigned_by=request.user,
                notes=notes,
            )

            asset.client = client
            asset.homeworker = homeworker
            asset.status = Asset.Status.ASSIGNED
            asset.save()

            notify_device_assigned(asset, client=client, homeworker=homeworker)

            target_name = client.company_name if client else homeworker.name
            if is_htmx(request):
                return _hx_toast('success', f'Asset assigned to {target_name}.', status=204, extra_events={'asset-saved': True})
            messages.success(request, f'Asset assigned to {target_name}.')
            return redirect('assets:asset_detail', pk=asset.pk)
    else:
        form = AssetAssignForm()

    template = 'assets/_asset_assign_partial.html' if is_htmx(request) else 'assets/asset_assign.html'
    return render(request, template, {'form': form, 'obj': asset, 'page_title': f'Assign Asset — {asset.asset_tag}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['POST'])
@transaction.atomic
def asset_return_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if asset.status != Asset.Status.ASSIGNED:
        if is_htmx(request):
            return _hx_toast('error', 'Asset is not currently assigned.', status=200)
        messages.error(request, 'Asset is not currently assigned.')
        return redirect('assets:asset_detail', pk=asset.pk)

    assignment = asset.assignments.filter(return_date__isnull=True).first()
    if assignment:
        assignment.return_date = timezone.now()
        assignment.save()

    asset.client = None
    asset.homeworker = None
    asset.status = Asset.Status.AVAILABLE
    asset.save()

    if is_htmx(request):
        return _hx_toast('success', 'Asset returned successfully.', status=204, extra_events={'asset-saved': True})
    messages.success(request, 'Asset returned successfully.')
    return redirect('assets:asset_detail', pk=asset.pk)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_status_change_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        homeworker_id = request.POST.get('homeworker', '')
        if new_status in dict(Asset.Status.choices):
            if new_status == Asset.Status.ASSIGNED and not homeworker_id:
                if is_htmx(request):
                    return _hx_toast('error', 'Homeworker is required when setting status to Assigned.', status=200)
                messages.error(request, 'Homeworker is required when setting status to Assigned.')
                return redirect('assets:asset_detail', pk=asset.pk)

            asset.status = new_status
            if new_status == Asset.Status.ASSIGNED and homeworker_id:
                from clients.models import Homeworker
                hw = Homeworker.objects.filter(pk=homeworker_id, is_active=True).first()
                if hw:
                    asset.homeworker = hw
            elif new_status != Asset.Status.ASSIGNED:
                asset.homeworker = None
                asset.client = None
            asset.save()
            if is_htmx(request):
                return _hx_toast('success', f'Status changed to {asset.get_status_display()}.', status=204, extra_events={'asset-saved': True})
            messages.success(request, f'Status changed to {asset.get_status_display()}.')
        else:
            if is_htmx(request):
                return _hx_toast('error', 'Invalid status.', status=200)
            messages.error(request, 'Invalid status.')
        return redirect('assets:asset_detail', pk=asset.pk)

    from clients.models import Homeworker
    context = {
        'obj': asset,
        'statuses': Asset.Status.choices,
        'homeworkers': Homeworker.objects.filter(is_active=True),
    }
    return render(request, 'assets/_asset_status_change_partial.html', context)


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_detail_pdf(request, pk):
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    asset = get_object_or_404(
        Asset.objects.select_related('asset_type', 'client', 'homeworker__client'),
        pk=pk
    )

    if request.user.is_client and (not asset.client or asset.client.user != request.user):
        return HttpResponseForbidden('You do not have access to this asset.')

    assignments = asset.assignments.select_related('client', 'homeworker__client', 'assigned_by')[:10]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f'Asset Report — {asset.asset_tag}', styles['Title']))
    elements.append(Spacer(1, 8*mm))

    def field_row(label, value):
        return [Paragraph(f'<b>{label}</b>', styles['Normal']), Paragraph(str(value) if value else '—', styles['Normal'])]

    details_data = [
        field_row('Asset Tag', asset.asset_tag),
        field_row('Serial Number', asset.serial_number),
        field_row('Type', asset.asset_type.name),
        field_row('Brand', asset.brand),
        field_row('Model', asset.model_name),
        field_row('Location', asset.location),
        field_row('Status', asset.get_status_display()),
        field_row('Active', 'Yes' if asset.is_active else 'No'),
    ]
    t = Table(details_data, colWidths=[45*mm, 120*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(Paragraph('<b>Asset Details</b>', styles['Heading2']))
    elements.append(t)
    elements.append(Spacer(1, 6*mm))

    purchase_data = [
        field_row('Purchase Date', asset.purchase_date),
        field_row('Purchase Price', f'₹{asset.purchase_price}' if asset.purchase_price else ''),
        field_row('Warranty Expiry', asset.warranty_expiry),
        field_row('Holder', asset.holder_name),
    ]
    t2 = Table(purchase_data, colWidths=[45*mm, 120*mm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(Paragraph('<b>Purchase Info</b>', styles['Heading2']))
    elements.append(t2)
    elements.append(Spacer(1, 6*mm))

    if asset.specifications:
        elements.append(Paragraph('<b>Specifications</b>', styles['Heading2']))
        elements.append(Paragraph(asset.specifications.replace('\n', '<br/>'), styles['Normal']))
        elements.append(Spacer(1, 6*mm))

    if asset.notes:
        elements.append(Paragraph('<b>Notes</b>', styles['Heading2']))
        elements.append(Paragraph(asset.notes.replace('\n', '<br/>'), styles['Normal']))
        elements.append(Spacer(1, 6*mm))

    if assignments:
        elements.append(Paragraph('<b>Assignment History</b>', styles['Heading2']))
        assignment_data = [['Assigned To', 'Assigned By', 'Date', 'Returned']]
        for a in assignments:
            assigned_to = a.client.company_name if a.client else (a.homeworker.name if a.homeworker else '—')
            assignment_data.append([
                assigned_to,
                a.assigned_by.get_full_name(),
                a.assigned_date.strftime('%b %d, %Y %I:%M %p') if a.assigned_date else '—',
                a.return_date.strftime('%b %d, %Y %I:%M %p') if a.return_date else 'Current',
            ])
        t3 = Table(assignment_data, colWidths=[45*mm, 40*mm, 40*mm, 40*mm])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t3)

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="asset_{asset.asset_tag}.pdf"'
    return response
