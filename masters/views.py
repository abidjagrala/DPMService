import json

from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, login_required, role_required

from .forms import (
    AssetTypeForm,
    CityForm,
    ServiceTypeForm,
    StateForm,
    TransportTypeForm,
)
from .models import AssetType, City, ServiceType, State, TransportType


def _hx_toast(level: str, message: str, status: int = 200, extra_events: dict | None = None) -> HttpResponse:
    payload: dict = {
        'toast': {'level': level, 'message': str(message)},
    }
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


def _hx_redirect(url: str, level: str | None = None, message: str | None = None) -> HttpResponse:
    response = HttpResponse(status=200)
    response['HX-Redirect'] = url
    if level and message:
        response['HX-Trigger'] = json.dumps({'toast': {'level': level, 'message': str(message)}})
    return response


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def state_list_view(request):
    states = State.objects.all()
    search = request.GET.get('search', '').strip()
    if search:
        states = states.filter(name__icontains=search)
    context = {'states': states, 'search': search, 'page_title': 'States'}
    if is_htmx(request):
        return render(request, 'masters/_state_list_table.html', context)
    return render(request, 'masters/state_list.html', context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def state_create_view(request):
    if request.method == 'POST':
        form = StateForm(request.POST)
        if form.is_valid():
            state = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'State {state.name} created.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'State {state.name} created successfully.')
            return redirect('masters:state_list')
    else:
        form = StateForm()

    template = 'masters/_state_form_partial.html' if is_htmx(request) else 'masters/state_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add State'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def state_update_view(request, pk):
    state = get_object_or_404(State, pk=pk)
    if request.method == 'POST':
        form = StateForm(request.POST, instance=state)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'State {state.name} updated.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'State {state.name} updated successfully.')
            return redirect('masters:state_list')
    else:
        form = StateForm(instance=state)

    template = 'masters/_state_form_partial.html' if is_htmx(request) else 'masters/state_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': state, 'page_title': f'Edit State — {state.name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def state_delete_view(request, pk):
    state = get_object_or_404(State, pk=pk)
    if request.method == 'POST':
        name = state.name
        state.delete()
        if is_htmx(request):
            return _hx_toast('success', f'State {name} deleted.', status=204, extra_events={'master-saved': True})
        messages.success(request, f'State {name} deleted successfully.')
        return redirect('masters:state_list')

    template = 'masters/_state_confirm_delete_partial.html' if is_htmx(request) else 'masters/state_confirm_delete.html'
    return render(request, template, {'obj': state, 'page_title': f'Delete State — {state.name}'})


# ---------------------------------------------------------------------------
# City
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def city_list_view(request):
    cities = City.objects.select_related('state').all()
    search = request.GET.get('search', '').strip()
    state_filter = request.GET.get('state', '')
    if search:
        from django.db.models import Q
        cities = cities.filter(Q(name__icontains=search) | Q(state__name__icontains=search))
    if state_filter:
        cities = cities.filter(state_id=state_filter)
    states = State.objects.filter(is_active=True)
    context = {
        'cities': cities,
        'states': states,
        'search': search,
        'selected_state': state_filter,
        'page_title': 'Cities',
    }
    if is_htmx(request):
        return render(request, 'masters/_city_list_table.html', context)
    return render(request, 'masters/city_list.html', context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def city_create_view(request):
    if request.method == 'POST':
        form = CityForm(request.POST)
        if form.is_valid():
            city = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'City {city.name} created.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'City {city.name} created successfully.')
            return redirect('masters:city_list')
    else:
        form = CityForm()

    template = 'masters/_city_form_partial.html' if is_htmx(request) else 'masters/city_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add City'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def city_update_view(request, pk):
    city = get_object_or_404(City, pk=pk)
    if request.method == 'POST':
        form = CityForm(request.POST, instance=city)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'City {city.name} updated.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'City {city.name} updated successfully.')
            return redirect('masters:city_list')
    else:
        form = CityForm(instance=city)

    template = 'masters/_city_form_partial.html' if is_htmx(request) else 'masters/city_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': city, 'page_title': f'Edit City — {city.name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def city_delete_view(request, pk):
    city = get_object_or_404(City, pk=pk)
    if request.method == 'POST':
        name = city.name
        city.delete()
        if is_htmx(request):
            return _hx_toast('success', f'City {name} deleted.', status=204, extra_events={'master-saved': True})
        messages.success(request, f'City {name} deleted successfully.')
        return redirect('masters:city_list')

    template = 'masters/_city_confirm_delete_partial.html' if is_htmx(request) else 'masters/city_confirm_delete.html'
    return render(request, template, {'obj': city, 'page_title': f'Delete City — {city.name}'})


# ---------------------------------------------------------------------------
# ServiceType
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def service_type_list_view(request):
    service_types = ServiceType.objects.all()
    context = {'service_types': service_types, 'page_title': 'Service Types'}
    if is_htmx(request):
        return render(request, 'masters/_service_type_list_table.html', context)
    return render(request, 'masters/service_type_list.html', context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def service_type_create_view(request):
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST)
        if form.is_valid():
            st = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Service type {st.name} created.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'Service type {st.name} created successfully.')
            return redirect('masters:service_type_list')
    else:
        form = ServiceTypeForm()

    template = 'masters/_service_type_form_partial.html' if is_htmx(request) else 'masters/service_type_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Service Type'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def service_type_update_view(request, pk):
    st = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, instance=st)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Service type {st.name} updated.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'Service type {st.name} updated successfully.')
            return redirect('masters:service_type_list')
    else:
        form = ServiceTypeForm(instance=st)

    template = 'masters/_service_type_form_partial.html' if is_htmx(request) else 'masters/service_type_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': st, 'page_title': f'Edit Service Type — {st.name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def service_type_delete_view(request, pk):
    st = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        name = st.name
        st.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Service type {name} deleted.', status=204, extra_events={'master-saved': True})
        messages.success(request, f'Service type {name} deleted successfully.')
        return redirect('masters:service_type_list')

    template = 'masters/_service_type_confirm_delete_partial.html' if is_htmx(request) else 'masters/service_type_confirm_delete.html'
    return render(request, template, {'obj': st, 'page_title': f'Delete Service Type — {st.name}'})


# ---------------------------------------------------------------------------
# AssetType
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def asset_type_list_view(request):
    asset_types = AssetType.objects.all()
    context = {'asset_types': asset_types, 'page_title': 'Asset Types'}
    if is_htmx(request):
        return render(request, 'masters/_asset_type_list_table.html', context)
    return render(request, 'masters/asset_type_list.html', context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_type_create_view(request):
    if request.method == 'POST':
        form = AssetTypeForm(request.POST)
        if form.is_valid():
            at = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Asset type {at.name} created.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'Asset type {at.name} created successfully.')
            return redirect('masters:asset_type_list')
    else:
        form = AssetTypeForm()

    template = 'masters/_asset_type_form_partial.html' if is_htmx(request) else 'masters/asset_type_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Asset Type'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_type_update_view(request, pk):
    at = get_object_or_404(AssetType, pk=pk)
    if request.method == 'POST':
        form = AssetTypeForm(request.POST, instance=at)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Asset type {at.name} updated.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'Asset type {at.name} updated successfully.')
            return redirect('masters:asset_type_list')
    else:
        form = AssetTypeForm(instance=at)

    template = 'masters/_asset_type_form_partial.html' if is_htmx(request) else 'masters/asset_type_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': at, 'page_title': f'Edit Asset Type — {at.name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def asset_type_delete_view(request, pk):
    at = get_object_or_404(AssetType, pk=pk)
    if request.method == 'POST':
        name = at.name
        at.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Asset type {name} deleted.', status=204, extra_events={'master-saved': True})
        messages.success(request, f'Asset type {name} deleted successfully.')
        return redirect('masters:asset_type_list')

    template = 'masters/_asset_type_confirm_delete_partial.html' if is_htmx(request) else 'masters/asset_type_confirm_delete.html'
    return render(request, template, {'obj': at, 'page_title': f'Delete Asset Type — {at.name}'})


# ---------------------------------------------------------------------------
# TransportType
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def transport_type_list_view(request):
    transport_types = TransportType.objects.all()
    context = {'transport_types': transport_types, 'page_title': 'Transport Types'}
    if is_htmx(request):
        return render(request, 'masters/_transport_type_list_table.html', context)
    return render(request, 'masters/transport_type_list.html', context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def transport_type_create_view(request):
    if request.method == 'POST':
        form = TransportTypeForm(request.POST)
        if form.is_valid():
            tt = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Transport type {tt.name} created.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'Transport type {tt.name} created successfully.')
            return redirect('masters:transport_type_list')
    else:
        form = TransportTypeForm()

    template = 'masters/_transport_type_form_partial.html' if is_htmx(request) else 'masters/transport_type_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Transport Type'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def transport_type_update_view(request, pk):
    tt = get_object_or_404(TransportType, pk=pk)
    if request.method == 'POST':
        form = TransportTypeForm(request.POST, instance=tt)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Transport type {tt.name} updated.', status=204, extra_events={'master-saved': True})
            messages.success(request, f'Transport type {tt.name} updated successfully.')
            return redirect('masters:transport_type_list')
    else:
        form = TransportTypeForm(instance=tt)

    template = 'masters/_transport_type_form_partial.html' if is_htmx(request) else 'masters/transport_type_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': tt, 'page_title': f'Edit Transport Type — {tt.name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def transport_type_delete_view(request, pk):
    tt = get_object_or_404(TransportType, pk=pk)
    if request.method == 'POST':
        name = tt.name
        tt.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Transport type {name} deleted.', status=204, extra_events={'master-saved': True})
        messages.success(request, f'Transport type {name} deleted successfully.')
        return redirect('masters:transport_type_list')

    template = 'masters/_transport_type_confirm_delete_partial.html' if is_htmx(request) else 'masters/transport_type_confirm_delete.html'
    return render(request, template, {'obj': tt, 'page_title': f'Delete Transport Type — {tt.name}'})
