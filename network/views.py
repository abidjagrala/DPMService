import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, role_required

from .forms import NetworkDeviceForm
from .models import NetworkDevice


def _hx_toast(level: str, message: str, status: int = 200, extra_events: dict | None = None) -> HttpResponse:
    payload: dict = {
        'toast': {'level': level, 'message': str(message)},
    }
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


# ---------------------------------------------------------------------------
# Network Device
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def device_list_view(request):
    devices = NetworkDevice.objects.select_related('client').all()
    search = request.GET.get('search', '').strip()
    type_filter = request.GET.get('type', '')
    client_filter = request.GET.get('client', '')

    if search:
        devices = devices.filter(
            Q(name__icontains=search) |
            Q(device_type__icontains=search) |
            Q(brand__icontains=search) |
            Q(client__company_name__icontains=search)
        )
    if type_filter in dict(NetworkDevice.DeviceType.choices):
        devices = devices.filter(device_type=type_filter)
    if client_filter:
        devices = devices.filter(client_id=client_filter)

    from clients.models import Client
    page = request.GET.get('page', 1)
    paginator = Paginator(devices, 50)
    page_obj = paginator.get_page(page)

    context = {
        'devices': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'device_types': NetworkDevice.DeviceType.choices,
        'clients': Client.objects.filter(is_active=True),
        'selected_type': type_filter,
        'selected_client': client_filter,
        'search': search,
        'page_title': 'Network Devices',
    }
    if is_htmx(request):
        return render(request, 'network/_device_list_page.html', context)
    return render(request, 'network/device_list.html', context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def device_create_view(request):
    if request.method == 'POST':
        form = NetworkDeviceForm(request.POST)
        if form.is_valid():
            device = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Device {device.name} created.', status=204, extra_events={'network-saved': True})
            messages.success(request, f'Device {device.name} created successfully.')
            return redirect('network:device_list')
    else:
        form = NetworkDeviceForm()

    template = 'network/_device_form_partial.html' if is_htmx(request) else 'network/device_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Network Device'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def device_multi_create_view(request):
    from clients.models import Client

    if request.method == 'POST':
        name_prefix = request.POST.get('name_prefix', '').strip()
        starting_ip = request.POST.get('starting_ip', '').strip()
        client_id = request.POST.get('client', '')
        count = int(request.POST.get('count', 1))

        if not name_prefix or not starting_ip or count < 1:
            if is_htmx(request):
                return HttpResponse('<div class="alert alert-error">Please fill in all required fields.</div>', status=400)
            messages.error(request, 'Please fill in all required fields.')
            return redirect('network:device_list')

        client = None
        if client_id:
            client = Client.objects.filter(pk=client_id).first()

        created_devices = []
        errors = []
        for i in range(count):
            submitted_name = request.POST.get(f'name_{i}', '').strip()
            submitted_ip = request.POST.get(f'ip_{i}', '').strip()
            if submitted_name:
                device_name = submitted_name
            else:
                device_name = f'{name_prefix} {i + 1}' if count > 1 else name_prefix
            device_ip = submitted_ip if submitted_ip else starting_ip
            brand = request.POST.get(f'brand_{i}', '').strip()
            device_type = request.POST.get(f'device_type_{i}', NetworkDevice.DeviceType.OTHER)

            device = NetworkDevice(
                name=device_name,
                device_type=device_type,
                ip_address=device_ip,
                brand=brand,
                client=client,
            )
            try:
                device.full_clean()
                device.save()
                created_devices.append(device_name)
            except Exception as e:
                errors.append(f'{device_name}: {e}')

        if is_htmx(request):
            if errors:
                return HttpResponse(f'<div class="alert alert-warning">{len(created_devices)} created, {len(errors)} failed: {"; ".join(errors)}</div>', status=207)
            return _hx_toast('success', f'{len(created_devices)} devices created.', status=204, extra_events={'network-saved': True})

        if errors:
            messages.warning(request, f'{len(created_devices)} created, {len(errors)} failed.')
        else:
            messages.success(request, f'{len(created_devices)} devices created successfully.')
        return redirect('network:device_list')

    context = {
        'device_types': NetworkDevice.DeviceType.choices,
        'clients': Client.objects.filter(is_active=True),
        'page_title': 'Add Multiple Devices',
    }
    template = 'network/_device_multi_form_partial.html' if is_htmx(request) else 'network/device_multi_form.html'
    return render(request, template, context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def device_update_view(request, pk):
    device = get_object_or_404(NetworkDevice, pk=pk)
    if request.method == 'POST':
        form = NetworkDeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Device {device.name} updated.', status=204, extra_events={'network-saved': True})
            messages.success(request, f'Device {device.name} updated successfully.')
            return redirect('network:device_list')
    else:
        form = NetworkDeviceForm(instance=device)

    template = 'network/_device_form_partial.html' if is_htmx(request) else 'network/device_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': device, 'page_title': f'Edit Device — {device.name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def device_delete_view(request, pk):
    device = get_object_or_404(NetworkDevice, pk=pk)
    if request.method == 'POST':
        name = device.name
        device.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Device {name} deleted.', status=204, extra_events={'network-saved': True})
        messages.success(request, f'Device {name} deleted successfully.')
        return redirect('network:device_list')

    template = 'network/_device_confirm_delete_partial.html' if is_htmx(request) else 'network/device_confirm_delete.html'
    return render(request, template, {'obj': device, 'page_title': f'Delete Device — {device.name}'})


@role_required('admin', 'manager', 'staff')
@require_http_methods(['GET'])
def device_detail_view(request, pk):
    device = get_object_or_404(NetworkDevice.objects.select_related('client'), pk=pk)
    return render(request, 'network/device_detail.html', {'obj': device, 'page_title': device.name})
