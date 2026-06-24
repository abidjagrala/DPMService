import csv
import io
import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, role_required
from clients.models import Client

from .forms import DomainHostingForm, DomainHostingInvoiceForm
from .models import DomainHosting, DomainHostingInvoice


def _hx_toast(level: str, message: str, status: int = 200, extra_events: dict | None = None) -> HttpResponse:
    payload: dict = {
        'toast': {'level': level, 'message': str(message)},
    }
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


def _get_filtered_services(request):
    services = DomainHosting.objects.select_related('client').all()
    search = request.GET.get('search', '').strip()
    service_type = request.GET.get('service_type', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')

    if search:
        services = services.filter(
            Q(service_name__icontains=search) |
            Q(client__company_name__icontains=search) |
            Q(provider__icontains=search)
        )
    if service_type:
        services = services.filter(service_type=service_type)
    if status_filter:
        services = services.filter(status=status_filter)
    if client_filter:
        services = services.filter(client_id=client_filter)
    return services


# ---------------------------------------------------------------------------
# DomainHosting CRUD
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def hosting_list_view(request):
    services = _get_filtered_services(request)

    page_num = request.GET.get('page', 1)
    paginator = Paginator(services, 50)
    page_obj = paginator.get_page(page_num)

    context = {
        'services': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': request.GET.get('search', ''),
        'selected_service_type': request.GET.get('service_type', ''),
        'selected_status': request.GET.get('status', ''),
        'selected_client': request.GET.get('client', ''),
        'service_type_choices': DomainHosting.ServiceType.choices,
        'status_choices': DomainHosting.Status.choices,
        'clients': Client.objects.filter(is_active=True),
        'page_title': 'Domain and Hosting Services',
    }
    if is_htmx(request):
        return render(request, 'hosting/_hosting_list_content.html', context)
    return render(request, 'hosting/hosting_list.html', context)


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def hosting_export_csv(request):
    services = _get_filtered_services(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="hosting_services.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Client', 'Service Type', 'Service Name', 'Provider',
        'Registration Date', 'Expiry Date', 'Days Left',
        'Renewal Amount', 'GST %', 'Total', 'Status',
    ])
    for s in services:
        writer.writerow([
            s.client.company_name,
            s.get_service_type_display(),
            s.service_name,
            s.provider,
            s.registration_date,
            s.expiry_date,
            s.days_until_expiry,
            s.renewal_amount,
            s.gst_percent,
            s.renewal_with_gst,
            s.get_status_display(),
        ])
    return response


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def hosting_create_view(request):
    if request.method == 'POST':
        form = DomainHostingForm(request.POST)
        if form.is_valid():
            service = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'{service.service_name} created.', status=204, extra_events={'hosting-saved': True})
            messages.success(request, f'{service.service_name} created successfully.')
            return redirect('hosting:hosting_list')
    else:
        form = DomainHostingForm()

    template = 'hosting/_hosting_form_partial.html' if is_htmx(request) else 'hosting/hosting_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Service'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def hosting_update_view(request, pk):
    service = get_object_or_404(DomainHosting, pk=pk)
    if request.method == 'POST':
        form = DomainHostingForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'{service.service_name} updated.', status=204, extra_events={'hosting-saved': True})
            messages.success(request, f'{service.service_name} updated successfully.')
            return redirect('hosting:hosting_list')
    else:
        form = DomainHostingForm(instance=service)

    template = 'hosting/_hosting_form_partial.html' if is_htmx(request) else 'hosting/hosting_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': service, 'page_title': f'Edit — {service.service_name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def hosting_delete_view(request, pk):
    service = get_object_or_404(DomainHosting, pk=pk)
    if request.method == 'POST':
        name = service.service_name
        service.delete()
        if is_htmx(request):
            return _hx_toast('success', f'{name} deleted.', status=204, extra_events={'hosting-saved': True})
        messages.success(request, f'{name} deleted successfully.')
        return redirect('hosting:hosting_list')

    template = 'hosting/_hosting_confirm_delete_partial.html' if is_htmx(request) else 'hosting/hosting_confirm_delete.html'
    return render(request, template, {'obj': service, 'page_title': f'Delete — {service.service_name}'})


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def hosting_detail_view(request, pk):
    service = get_object_or_404(DomainHosting.objects.select_related('client'), pk=pk)
    invoices = service.invoices.all()
    invoice_form = DomainHostingInvoiceForm()
    return render(request, 'hosting/hosting_detail.html', {
        'obj': service,
        'invoices': invoices,
        'invoice_form': invoice_form,
        'page_title': service.service_name,
    })


# ---------------------------------------------------------------------------
# Invoice CRUD (nested under hosting detail)
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def hosting_invoice_create_view(request, service_pk):
    service = get_object_or_404(DomainHosting, pk=service_pk)
    if request.method == 'POST':
        form = DomainHostingInvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.service = service
            invoice.save()
            if is_htmx(request):
                return _hx_toast('success', f'Invoice added for {service.service_name}.', status=204, extra_events={'invoice-saved': True})
            messages.success(request, f'Invoice added for {service.service_name}.')
            return redirect('hosting:hosting_detail', pk=service.pk)
    else:
        form = DomainHostingInvoiceForm()

    template = 'hosting/_invoice_form_partial.html' if is_htmx(request) else 'hosting/hosting_detail.html'
    return render(request, template, {
        'form': form,
        'obj': service,
        'mode': 'create',
        'page_title': f'Add Invoice — {service.service_name}',
    })


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def hosting_invoice_delete_view(request, service_pk, pk):
    invoice = get_object_or_404(DomainHostingInvoice, pk=pk, service_id=service_pk)
    service = invoice.service
    if request.method == 'POST':
        invoice.delete()
        if is_htmx(request):
            return _hx_toast('success', 'Invoice deleted.', status=204, extra_events={'invoice-saved': True})
        messages.success(request, 'Invoice deleted successfully.')
        return redirect('hosting:hosting_detail', pk=service.pk)

    template = 'hosting/_invoice_confirm_delete_partial.html' if is_htmx(request) else 'hosting/hosting_detail.html'
    return render(request, template, {
        'obj': invoice,
        'service': service,
        'page_title': f'Delete Invoice — {service.service_name}',
    })


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def hosting_download_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="hosting_import_template.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'client', 'service_type', 'service_name', 'provider',
        'registration_date', 'expiry_date', 'renewal_amount', 'gst_percent',
        'status', 'nameserver', 'ip_address', 'notes', 'is_active',
    ])
    writer.writerow([
        'Acme Corp', 'domain', 'example.com', 'GoDaddy',
        '2024-01-15', '2025-01-15', '1500.00', '18',
        'active', 'ns1.example.com', '192.168.1.1', 'Primary domain', 'true',
    ])
    return response


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def hosting_import_csv(request):
    if request.method == 'GET':
        return render(request, 'hosting/hosting_import.html', {'page_title': 'Import Domain & Hosting Services'})

    confirm = request.POST.get('confirm')

    uploaded_file = request.FILES.get('csv_file')
    if not uploaded_file:
        messages.error(request, 'Please select a CSV file to upload.')
        return redirect('hosting:hosting_import')

    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        messages.error(request, 'Could not read the CSV file. Please check the format.')
        return redirect('hosting:hosting_import')

    required = ['client', 'service_type', 'service_name', 'registration_date', 'expiry_date']
    headers = reader.fieldnames or []
    missing = [h for h in required if h not in headers]
    if missing:
        messages.error(request, f'Missing required columns: {", ".join(missing)}')
        return redirect('hosting:hosting_import')

    # Batch-load FK lookups
    client_map = {c.company_name.lower(): c for c in Client.objects.filter(is_active=True)}

    valid_service_types = {v for v, _ in DomainHosting.ServiceType.choices}
    valid_statuses = {v for v, _ in DomainHosting.Status.choices}

    rows = []
    valid_count = 0
    for i, row in enumerate(reader, start=2):
        errors = []
        client_name = (row.get('client') or '').strip()
        service_type = (row.get('service_type') or '').strip().lower()
        service_name = (row.get('service_name') or '').strip()
        provider = (row.get('provider') or '').strip()
        reg_date = (row.get('registration_date') or '').strip()
        exp_date = (row.get('expiry_date') or '').strip()
        renewal = (row.get('renewal_amount') or '0').strip()
        gst = (row.get('gst_percent') or '18').strip()
        status = (row.get('status') or 'active').strip().lower()
        nameserver = (row.get('nameserver') or '').strip()
        ip = (row.get('ip_address') or '').strip()
        notes = (row.get('notes') or '').strip()
        active_raw = (row.get('is_active') or 'true').strip().lower()
        is_active = active_raw in ('true', '1', 'yes')

        if not client_name:
            errors.append('client is required')
        elif client_name.lower() not in client_map:
            errors.append(f'client "{client_name}" not found')
        if not service_type:
            errors.append('service_type is required')
        elif service_type not in valid_service_types:
            errors.append(f'service_type must be one of: {", ".join(valid_service_types)}')
        if not service_name:
            errors.append('service_name is required')
        if not reg_date:
            errors.append('registration_date is required')
        else:
            try:
                from datetime import datetime
                datetime.strptime(reg_date, '%Y-%m-%d')
            except ValueError:
                errors.append('registration_date must be YYYY-MM-DD format')
        if not exp_date:
            errors.append('expiry_date is required')
        else:
            try:
                from datetime import datetime
                datetime.strptime(exp_date, '%Y-%m-%d')
            except ValueError:
                errors.append('expiry_date must be YYYY-MM-DD format')
        if status not in valid_statuses:
            errors.append(f'status must be one of: {", ".join(valid_statuses)}')
        try:
            float(renewal)
        except ValueError:
            errors.append('renewal_amount must be a number')
        try:
            float(gst)
        except ValueError:
            errors.append('gst_percent must be a number')
        if ip:
            from django.core.validators import validate_ipv46_address
            from django.core.exceptions import ValidationError
            try:
                validate_ipv46_address(ip)
            except ValidationError:
                errors.append('ip_address is not valid')

        row_data = {
            'row': i,
            'client': client_name,
            'service_type': service_type,
            'service_name': service_name,
            'provider': provider,
            'registration_date': reg_date,
            'expiry_date': exp_date,
            'renewal_amount': renewal,
            'gst_percent': gst,
            'status': status,
            'nameserver': nameserver,
            'ip_address': ip,
            'notes': notes,
            'is_active': is_active,
            'errors': errors,
        }
        rows.append(row_data)
        if not errors:
            valid_count += 1

    if confirm == 'yes' and valid_count > 0:
        created = 0
        with transaction.atomic():
            for r in rows:
                if r['errors']:
                    continue
                DomainHosting.objects.create(
                    client=client_map[r['client'].lower()],
                    service_type=r['service_type'],
                    service_name=r['service_name'],
                    provider=r['provider'],
                    registration_date=r['registration_date'],
                    expiry_date=r['expiry_date'],
                    renewal_amount=r['renewal_amount'],
                    gst_percent=r['gst_percent'],
                    status=r['status'],
                    nameserver=r['nameserver'],
                    ip_address=r['ip_address'] or None,
                    notes=r['notes'],
                    is_active=r['is_active'],
                )
                created += 1
        if is_htmx(request):
            return _hx_toast('success', f'{created} service(s) imported.', status=204, extra_events={'hosting-saved': True})
        messages.success(request, f'{created} service(s) imported successfully.')
        return redirect('hosting:hosting_list')

    context = {
        'page_title': 'Import Domain & Hosting Services',
        'rows': rows,
        'valid_count': valid_count,
        'error_count': len(rows) - valid_count,
    }
    if is_htmx(request):
        return render(request, 'hosting/_hosting_import_preview.html', context)
    return render(request, 'hosting/hosting_import.html', context)
