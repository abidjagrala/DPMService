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
    assets = Asset.objects.select_related('asset_type', 'client', 'client__branch').all()

    if request.user.is_client:
        assets = assets.filter(client__user=request.user)
    elif request.user.is_staff_member:
        branch_ids = list(request.user.employee_profile.branches.values_list('id', flat=True))
        if branch_ids:
            assets = assets.filter(client__branch_id__in=branch_ids)
        else:
            assets = assets.none()

    search = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')

    if search:
        assets = assets.filter(
            Q(serial_number__icontains=search) |
            Q(asset_type__name__icontains=search) |
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
    assets = Asset.objects.select_related('asset_type', 'client', 'client__branch').all()
    search = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    if search:
        assets = assets.filter(
            Q(serial_number__icontains=search) |
            Q(asset_type__name__icontains=search) |
            Q(client__company_name__icontains=search)
        )
    if type_filter:
        assets = assets.filter(asset_type_id=type_filter)
    if status_filter in dict(Asset.Status.choices):
        assets = assets.filter(status=status_filter)
    if request.user.is_client:
        assets = assets.filter(client__user=request.user)
    elif request.user.is_staff_member:
        branch_ids = list(request.user.employee_profile.branches.values_list('id', flat=True))
        if branch_ids:
            assets = assets.filter(client__branch_id__in=branch_ids)
        else:
            assets = assets.none()
    return assets


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_export_csv(request):
    assets = _get_filtered_assets(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="assets.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Serial Number', 'Type', 'Brand/Model',
        'Purchase Date', 'Warranty Expiry',
        'Status', 'Client', 'IP Address', 'MAC Address',
        'Notes', 'Active',
        'Created At', 'Updated At',
    ])
    for a in assets:
        writer.writerow([
            a.pk,
            a.serial_number,
            a.asset_type.name,
            a.brand_model,
            a.purchase_date or '',
            a.warranty_expiry or '',
            a.get_status_display(),
            a.client.company_name if a.client else '',
            a.ip_address,
            a.mac_address,
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
                return _hx_toast('success', f'Asset {asset.serial_number} created.', status=204, extra_events={'asset-saved': True})
            messages.success(request, f'Asset {asset.serial_number} created successfully.')
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
                return _hx_toast('success', f'Asset {asset.serial_number} updated.', status=204, extra_events={'asset-saved': True})
            messages.success(request, f'Asset {asset.serial_number} updated successfully.')
            return redirect('assets:asset_list')
    else:
        if request.user.is_client:
            from .forms import ClientAssetForm
            form = ClientAssetForm(instance=asset, user=request.user)
        else:
            form = AssetForm(instance=asset)

    template = 'assets/_asset_form_partial.html' if is_htmx(request) else 'assets/asset_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': asset, 'page_title': f'Edit Asset — {asset.serial_number}'})


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_delete_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if request.user.is_client and asset.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this asset.')

    if request.method == 'POST':
        serial = asset.serial_number
        asset.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Asset {serial} deleted.', status=204, extra_events={'asset-saved': True})
        messages.success(request, f'Asset {serial} deleted successfully.')
        return redirect('assets:asset_list')

    template = 'assets/_asset_confirm_delete_partial.html' if is_htmx(request) else 'assets/asset_confirm_delete.html'
    return render(request, template, {'obj': asset, 'page_title': f'Delete Asset — {asset.serial_number}'})


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_detail_view(request, pk):
    asset = get_object_or_404(
        Asset.objects.select_related('asset_type', 'client'),
        pk=pk
    )

    if request.user.is_client and (not asset.client or asset.client.user != request.user):
        return HttpResponseForbidden('You do not have access to this asset.')

    assignments = asset.assignments.select_related('client', 'assigned_by')[:10]
    service_tickets = asset.service_tickets.select_related(
        'service_type', 'client', 'assigned_to__user',
    ).order_by('-created_at')[:20]
    return render(request, 'assets/asset_detail.html', {
        'obj': asset,
        'assignments': assignments,
        'service_tickets': service_tickets,
        'page_title': str(asset),
    })


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_credentials_view(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if request.user.is_client and (not asset.client or asset.client.user != request.user):
        return HttpResponseForbidden('You do not have access to this asset.')

    return render(request, 'assets/_asset_credentials_partial.html', {'obj': asset})


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
            notes = form.cleaned_data['notes']

            assignment = AssetAssignment.objects.create(
                asset=asset,
                client=client,
                assigned_by=request.user,
                notes=notes,
            )

            asset.client = client
            asset.status = Asset.Status.ASSIGNED
            asset.save()

            notify_device_assigned(asset, client=client)

            target_name = client.company_name
            if is_htmx(request):
                return _hx_toast('success', f'Asset assigned to {target_name}.', status=204, extra_events={'asset-saved': True})
            messages.success(request, f'Asset assigned to {target_name}.')
            return redirect('assets:asset_detail', pk=asset.pk)
    else:
        form = AssetAssignForm()

    template = 'assets/_asset_assign_partial.html' if is_htmx(request) else 'assets/asset_assign.html'
    return render(request, template, {'form': form, 'obj': asset, 'page_title': f'Assign Asset — {asset.serial_number}'})


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
        if new_status in dict(Asset.Status.choices):
            asset.status = new_status
            if new_status != Asset.Status.ASSIGNED:
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

    context = {
        'obj': asset,
        'statuses': Asset.Status.choices,
    }
    return render(request, 'assets/_asset_status_change_partial.html', context)


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def asset_detail_pdf(request, pk):
    from io import BytesIO
    from datetime import datetime, timezone as dt_timezone, timedelta

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    from reportlab.pdfgen.canvas import Canvas

    from accounts.models import CompanyInfo

    asset = get_object_or_404(
        Asset.objects.select_related('asset_type', 'client'),
        pk=pk
    )

    if request.user.is_client and (not asset.client or asset.client.user != request.user):
        return HttpResponseForbidden('You do not have access to this asset.')

    assignments = asset.assignments.select_related('client', 'assigned_by')[:10]
    company = CompanyInfo.get_instance()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=20 * mm, bottomMargin=25 * mm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    label_style = ParagraphStyle(
        'FieldLabel', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold', textColor=colors.Color(0.3, 0.3, 0.3),
    )
    value_style = ParagraphStyle(
        'FieldValue', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
    )
    heading_style = ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'],
        fontSize=11, fontName='Helvetica-Bold', spaceAfter=4 * mm,
        textColor=colors.Color(0.15, 0.15, 0.15),
    )

    def field_row(label, value):
        return [
            Paragraph(f'<b>{label}</b>', label_style),
            Paragraph(str(value) if value else 'Not Available', value_style),
        ]

    # ============================================================
    # HEADER
    # ============================================================
    logo_path = None
    if company.logo_light and hasattr(company.logo_light, 'path'):
        import os
        try:
            if os.path.exists(company.logo_light.path):
                logo_path = company.logo_light.path
        except Exception:
            logo_path = None

    if logo_path:
        from PIL import Image as PILImage
        with PILImage.open(logo_path) as img:
            orig_w, orig_h = img.size
        max_w, max_h = 35 * mm, 25 * mm
        ratio = min(max_w / orig_w, max_h / orig_h)
        logo_cell = RLImage(logo_path, width=orig_w * ratio, height=orig_h * ratio)
    else:
        logo_cell = Paragraph(
            f'<b>{company.name or "DPM Service"}</b>',
            ParagraphStyle('LogoText', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold')
        )

    address_lines = []
    if company.name:
        address_lines.append(f'<b>{company.name}</b>')
    if company.address:
        address_lines.append(company.address)
    city_parts = [p for p in [company.city, company.state, company.pincode] if p]
    if city_parts:
        address_lines.append(', '.join(city_parts))
    if company.country:
        address_lines.append(company.country)
    if company.phone:
        address_lines.append(f'Phone: {company.phone}')
    if company.email:
        address_lines.append(f'Email: {company.email}')
    if company.website:
        address_lines.append(f'Web: {company.website}')

    address_text = '<br/>'.join(address_lines) if address_lines else 'Not Available'
    address_para = Paragraph(address_text, ParagraphStyle(
        'Address', parent=styles['Normal'], fontSize=8, leading=11, alignment=2,
    ))

    header_data = [[logo_cell, address_para]]
    header_table = Table(header_data, colWidths=[80 * mm, 95 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6 * mm))

    # Title
    title_style = ParagraphStyle(
        'PDFTitle', parent=styles['Title'],
        fontSize=14, fontName='Helvetica-Bold', alignment=1,
        textColor=colors.Color(0.1, 0.1, 0.1),
    )
    elements.append(Paragraph(f'Asset Report — {asset.serial_number}', title_style))
    elements.append(Spacer(1, 6 * mm))

    # ============================================================
    # ASSET DETAILS — 4-column layout: Label | Value | Label | Value
    # ============================================================
    elements.append(Paragraph('Asset Details', heading_style))

    def val(v):
        return str(v) if v else 'Not Available'

    details_data = [
        field_row('Serial Number', asset.serial_number) + field_row('Type', asset.asset_type.name if asset.asset_type else None),
        field_row('Type', asset.asset_type.name if asset.asset_type else None) + field_row('Brand/Model', asset.brand_model),
        field_row('Client', asset.client.company_name if asset.client else None) + ['', ''],
        field_row('Device Location', asset.device_location),
        field_row('IP Address', asset.ip_address) + field_row('MAC Address', asset.mac_address),
        field_row('Username', asset.username) + field_row('Password', asset.password),
        field_row('Status', asset.get_status_display()) + field_row('Active', 'Yes' if asset.is_active else 'No'),
    ]
    t = Table(details_data, colWidths=[32 * mm, 55 * mm, 32 * mm, 55 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))

    # ============================================================
    # PURCHASE INFO — 4-column layout
    # ============================================================
    elements.append(Paragraph('Purchase Info', heading_style))

    purchase_data = [
        field_row('Purchase Date', asset.purchase_date) + field_row('Warranty Expiry', asset.warranty_expiry),
        field_row('Holder', asset.holder_name) + ['', ''],
    ]
    t2 = Table(purchase_data, colWidths=[32 * mm, 55 * mm, 32 * mm, 55 * mm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 4 * mm))

    # Notes
    elements.append(Paragraph('<b>Notes</b>', label_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(asset.notes.replace('\n', '<br/>') if asset.notes else 'Not Available', value_style))
    elements.append(Spacer(1, 8 * mm))

    # ============================================================
    # ASSIGNMENT HISTORY
    # ============================================================
    elements.append(Paragraph('Assignment History', heading_style))

    ah_header = [
        Paragraph('<b>Assigned To</b>', label_style),
        Paragraph('<b>Assigned By</b>', label_style),
        Paragraph('<b>Date</b>', label_style),
        Paragraph('<b>Returned</b>', label_style),
    ]
    ah_data = [ah_header]

    if assignments:
        for a in assignments:
            assigned_to = a.client.company_name if a.client else '—'
            assigned_by = a.assigned_by.get_full_name() if a.assigned_by else '—'
            ah_data.append([
                Paragraph(assigned_to, value_style),
                Paragraph(assigned_by, value_style),
                Paragraph(a.assigned_date.strftime('%d %b %Y, %I:%M %p') if a.assigned_date else '—', value_style),
                Paragraph(a.return_date.strftime('%d %b %Y, %I:%M %p') if a.return_date else 'Current', value_style),
            ])
    else:
        ah_data.append([
            Paragraph('No assignment records', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
        ])

    ah_table = Table(ah_data, colWidths=[45 * mm, 40 * mm, 45 * mm, 45 * mm])
    ah_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(ah_table)

    # ============================================================
    # FOOTER (on every page)
    # ============================================================
    ist = dt_timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    now_str = now_ist.strftime('%d %b %Y, %I:%M %p IST')
    user_name = request.user.get_full_name() or request.user.email

    class NumberedCanvas(Canvas):
        def __init__(self, *args, **kwargs):
            Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total_pages)
                Canvas.showPage(self)
            Canvas.save(self)

        def _draw_footer(self, total_pages):
            page_width = A4[0]
            self.saveState()
            self.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
            self.setLineWidth(0.5)
            self.line(15 * mm, 20 * mm, page_width - 15 * mm, 20 * mm)
            self.setFont('Helvetica', 7)
            self.setFillColor(colors.Color(0.5, 0.5, 0.5))
            self.drawString(15 * mm, 14 * mm, f'Generated: {now_str}')
            self.drawCentredString(page_width / 2, 14 * mm, f'Generated by: {user_name}')
            self.drawRightString(page_width - 15 * mm, 14 * mm, f'Page {self.getPageNumber()} of {total_pages}')
            self.restoreState()

    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="asset_{asset.serial_number}.pdf"'
    return response


@role_required('admin', 'manager', 'staff')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_quick_create_view(request):
    if request.method == 'POST':
        serial_number = request.POST.get('serial_number', '').strip()
        asset_type_id = request.POST.get('asset_type', '').strip()
        brand_model = request.POST.get('brand_model', '').strip()
        client_id = request.POST.get('client', '').strip()

        if not asset_type_id:
            return HttpResponse(json.dumps({'error': 'Asset type is required.'}), status=400, content_type='application/json')

        from masters.models import AssetType
        asset_type = get_object_or_404(AssetType, pk=asset_type_id)

        asset = Asset(
            asset_type=asset_type,
            brand_model=brand_model,
            serial_number=serial_number,
        )
        if client_id:
            from clients.models import Client
            asset.client = Client.objects.filter(pk=client_id).first()
        asset.save()

        return HttpResponse(json.dumps({'id': asset.pk, 'label': str(asset)}), status=201, content_type='application/json')

    from masters.models import AssetType
    asset_types = AssetType.objects.filter(is_active=True).order_by('name')
    return render(request, 'assets/_asset_quick_form_partial.html', {'asset_types': asset_types})
