import csv
import io
import json
import re

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, role_required
from masters.models import City, State

from .forms import ClientForm, EmployeeForm, HomeworkerForm
from .models import Client, Employee, Homeworker

User = get_user_model()


def _hx_toast(level: str, message: str, status: int = 200, extra_events: dict | None = None) -> HttpResponse:
    payload: dict = {
        'toast': {'level': level, 'message': str(message)},
    }
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


def _render_city_searchable_select(state_id, field_name='city'):
    """Return an HTML searchable-select for cities filtered by state."""
    from accounts.templatetags.daisy import _render_searchable_select
    cities = City.objects.filter(is_active=True).order_by('name')
    if state_id:
        cities = cities.filter(state_id=state_id)
    options = [(str(c.pk), c.name) for c in cities]
    return _render_searchable_select(field_name, '', options, 'Search...')


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def client_city_select_partial(request):
    state_id = request.GET.get('state', '')
    return HttpResponse(_render_city_searchable_select(state_id, 'city'))


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def client_list_view(request):
    clients = Client.objects.select_related('city', 'state').all()

    search = request.GET.get('search', '').strip()
    city_filter = request.GET.get('city', '')
    status_filter = request.GET.get('status', '')

    if search:
        clients = clients.filter(
            Q(company_name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(phone__icontains=search)
        )
    if city_filter:
        clients = clients.filter(city_id=city_filter)
    if status_filter == 'active':
        clients = clients.filter(is_active=True)
    elif status_filter == 'inactive':
        clients = clients.filter(is_active=False)

    cities = City.objects.filter(is_active=True)

    context = {
        'clients': clients,
        'search': search,
        'cities': cities,
        'selected_city': city_filter,
        'selected_status': status_filter,
        'page_title': 'Clients',
    }
    if is_htmx(request):
        return render(request, 'clients/_client_list_table.html', context)
    return render(request, 'clients/client_list.html', context)


def _get_filtered_clients(request):
    clients = Client.objects.select_related('city', 'state').all()
    search = request.GET.get('search', '').strip()
    city_filter = request.GET.get('city', '')
    status_filter = request.GET.get('status', '')
    if search:
        clients = clients.filter(
            Q(company_name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(phone__icontains=search)
        )
    if city_filter:
        clients = clients.filter(city_id=city_filter)
    if status_filter == 'active':
        clients = clients.filter(is_active=True)
    elif status_filter == 'inactive':
        clients = clients.filter(is_active=False)
    return clients


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def client_export_csv(request):
    clients = _get_filtered_clients(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clients.csv"'
    writer = csv.writer(response)
    writer.writerow(['Company', 'Contact', 'Phone', 'Email', 'City', 'State', 'Status'])
    for c in clients:
        writer.writerow([
            c.company_name,
            c.contact_person,
            c.phone,
            c.email,
            c.city.name if c.city else '',
            c.state.name if c.state else '',
            'Active' if c.is_active else 'Inactive',
        ])
    return response


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def client_create_view(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Client {client.company_name} created.', status=204, extra_events={'client-saved': True})
            messages.success(request, f'Client {client.company_name} created successfully.')
            return redirect('clients:client_list')
    else:
        form = ClientForm()

    template = 'clients/_client_form_partial.html' if is_htmx(request) else 'clients/client_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Client'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def client_update_view(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Client {client.company_name} updated.', status=204, extra_events={'client-saved': True})
            messages.success(request, f'Client {client.company_name} updated successfully.')
            return redirect('clients:client_list')
    else:
        form = ClientForm(instance=client)

    template = 'clients/_client_form_partial.html' if is_htmx(request) else 'clients/client_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': client, 'page_title': f'Edit Client — {client.company_name}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def client_delete_view(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        name = client.company_name
        client.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Client {name} deleted.', status=204, extra_events={'client-saved': True})
        messages.success(request, f'Client {name} deleted successfully.')
        return redirect('clients:client_list')

    template = 'clients/_client_confirm_delete_partial.html' if is_htmx(request) else 'clients/client_confirm_delete.html'
    return render(request, template, {'obj': client, 'page_title': f'Delete Client — {client.company_name}'})


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def client_detail_view(request, pk):
    client = get_object_or_404(Client.objects.select_related('city', 'state'), pk=pk)
    if is_htmx(request):
        return render(request, 'clients/_client_detail_partial.html', {'obj': client})
    return render(request, 'clients/client_detail.html', {
        'obj': client,
        'page_title': client.company_name,
    })


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def client_download_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="client_import_template.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'company_name', 'contact_person', 'email', 'phone', 'alt_phone',
        'address', 'city', 'state', 'pincode', 'gst_number', 'pan_number',
        'is_active',
    ])
    writer.writerow([
        'Acme Corp', 'John Doe', 'john@acme.com', '9876543210', '9876543211',
        '123 Business Park, MG Road', 'Mumbai', 'Maharashtra', '400001',
        '27AABCU9603R1ZM', 'ABCDE1234F', 'true',
    ])
    return response


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def client_import_csv(request):
    if request.method == 'GET':
        return render(request, 'clients/client_import.html', {'page_title': 'Import Clients'})

    # POST — either preview or confirm
    confirm = request.POST.get('confirm')

    uploaded_file = request.FILES.get('csv_file')
    if not uploaded_file:
        messages.error(request, 'Please select a CSV file to upload.')
        return redirect('clients:client_import')

    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        messages.error(request, 'Could not read the CSV file. Please check the format.')
        return redirect('clients:client_import')

    required = ['company_name', 'contact_person', 'email', 'phone', 'address', 'city', 'state', 'pincode']
    headers = reader.fieldnames or []
    missing = [h for h in required if h not in headers]
    if missing:
        messages.error(request, f'Missing required columns: {", ".join(missing)}')
        return redirect('clients:client_import')

    # Batch-load FK lookups
    city_map = {c.name.lower(): c for c in City.objects.filter(is_active=True)}
    state_map = {s.name.lower(): s for s in State.objects.filter(is_active=True)}
    existing_emails = set(
        Client.objects.filter(email__in=[
            (row.get('email') or '').strip().lower() for row in reader
        ]).values_list('email', flat=True)
    )
    reader = csv.DictReader(io.StringIO(decoded))  # reset iterator

    rows = []
    valid_count = 0
    for i, row in enumerate(reader, start=2):
        errors = []
        company = (row.get('company_name') or '').strip()
        contact = (row.get('contact_person') or '').strip()
        email = (row.get('email') or '').strip().lower()
        phone = (row.get('phone') or '').strip()
        alt_phone = (row.get('alt_phone') or '').strip()
        address = (row.get('address') or '').strip()
        city_name = (row.get('city') or '').strip()
        state_name = (row.get('state') or '').strip()
        pincode = (row.get('pincode') or '').strip()
        gst = (row.get('gst_number') or '').strip()
        pan = (row.get('pan_number') or '').strip()
        active_raw = (row.get('is_active') or 'true').strip().lower()
        is_active = active_raw in ('true', '1', 'yes')

        if not company:
            errors.append('company_name is required')
        if not contact:
            errors.append('contact_person is required')
        if not email:
            errors.append('email is required')
        elif email in existing_emails:
            errors.append('email already exists')
        if not phone:
            errors.append('phone is required')
        if not address:
            errors.append('address is required')
        if not city_name:
            errors.append('city is required')
        elif city_name.lower() not in city_map:
            errors.append(f'city "{city_name}" not found')
        if not state_name:
            errors.append('state is required')
        elif state_name.lower() not in state_map:
            errors.append(f'state "{state_name}" not found')
        if not pincode:
            errors.append('pincode is required')

        row_data = {
            'row': i,
            'company_name': company,
            'contact_person': contact,
            'email': email,
            'phone': phone,
            'alt_phone': alt_phone,
            'address': address,
            'city': city_name,
            'state': state_name,
            'pincode': pincode,
            'gst_number': gst,
            'pan_number': pan,
            'is_active': is_active,
            'errors': errors,
        }
        rows.append(row_data)
        if not errors:
            valid_count += 1
            existing_emails.add(email)

    if confirm == 'yes' and valid_count > 0:
        created = 0
        with transaction.atomic():
            for r in rows:
                if r['errors']:
                    continue
                Client.objects.create(
                    company_name=r['company_name'],
                    contact_person=r['contact_person'],
                    email=r['email'],
                    phone=r['phone'],
                    alt_phone=r['alt_phone'],
                    address=r['address'],
                    city=city_map[r['city'].lower()],
                    state=state_map[r['state'].lower()],
                    pincode=r['pincode'],
                    gst_number=r['gst_number'],
                    pan_number=r['pan_number'],
                    is_active=r['is_active'],
                )
                created += 1
        if is_htmx(request):
            return _hx_toast('success', f'{created} client(s) imported.', status=204, extra_events={'client-saved': True})
        messages.success(request, f'{created} client(s) imported successfully.')
        return redirect('clients:client_list')

    context = {
        'page_title': 'Import Clients',
        'rows': rows,
        'valid_count': valid_count,
        'error_count': len(rows) - valid_count,
    }
    if is_htmx(request):
        return render(request, 'clients/_client_import_preview.html', context)
    return render(request, 'clients/client_import.html', context)


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------

@role_required('admin', 'manager')
@require_http_methods(['GET'])
def employee_list_view(request):
    employees = Employee.objects.select_related('user', 'city', 'state').all()
    search = request.GET.get('search', '').strip()
    department_filter = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')
    if search:
        employees = employees.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(employee_id__icontains=search)
        )
    if department_filter:
        employees = employees.filter(department=department_filter)
    if status_filter == 'active':
        employees = employees.filter(is_active=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)

    context = {
        'employees': employees,
        'search': search,
        'department_choices': Employee.Department.choices,
        'selected_department': department_filter,
        'selected_status': status_filter,
        'page_title': 'Employees',
    }
    if is_htmx(request):
        return render(request, 'clients/_employee_list_table.html', context)
    return render(request, 'clients/employee_list.html', context)


def _get_filtered_employees(request):
    employees = Employee.objects.select_related('user', 'city', 'state').all()
    search = request.GET.get('search', '').strip()
    department_filter = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')
    if search:
        employees = employees.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(employee_id__icontains=search)
        )
    if department_filter:
        employees = employees.filter(department=department_filter)
    if status_filter == 'active':
        employees = employees.filter(is_active=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)
    return employees


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def employee_export_csv(request):
    employees = _get_filtered_employees(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employees.csv"'
    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Email', 'Designation', 'Department', 'Phone', 'City', 'State', 'Status'])
    for e in employees:
        writer.writerow([
            e.employee_id,
            e.user.get_full_name(),
            e.user.email,
            e.designation,
            e.get_department_display(),
            e.phone,
            e.city.name if e.city else '',
            e.state.name if e.state else '',
            'Active' if e.is_active else 'Inactive',
        ])
    return response


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def employee_create_view(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, is_create=True)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']

            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                role=User.Role.STAFF,
            )

            employee = form.save(commit=False)
            employee.user = user
            employee.save()

            if is_htmx(request):
                return _hx_toast('success', f'Employee {user.get_full_name()} created.', status=204, extra_events={'employee-saved': True})
            messages.success(request, f'Employee {user.get_full_name()} created successfully.')
            return redirect('clients:employee_list')
    else:
        form = EmployeeForm(is_create=True)

    template = 'clients/_employee_form_partial.html' if is_htmx(request) else 'clients/employee_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Employee'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def employee_update_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee, is_create=False)
        if form.is_valid():
            user = employee.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()

            form.save()

            if is_htmx(request):
                return _hx_toast('success', f'Employee {user.get_full_name()} updated.', status=204, extra_events={'employee-saved': True})
            messages.success(request, f'Employee {user.get_full_name()} updated successfully.')
            return redirect('clients:employee_list')
    else:
        form = EmployeeForm(
            instance=employee,
            is_create=False,
            initial={
                'first_name': employee.user.first_name,
                'last_name': employee.user.last_name,
                'email': employee.user.email,
            },
        )

    template = 'clients/_employee_form_partial.html' if is_htmx(request) else 'clients/employee_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': employee, 'page_title': f'Edit Employee — {employee.user.get_full_name()}'})


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def employee_delete_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        name = employee.user.get_full_name()
        user = employee.user
        employee.delete()
        user.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Employee {name} deleted.', status=204, extra_events={'employee-saved': True})
        messages.success(request, f'Employee {name} deleted successfully.')
        return redirect('clients:employee_list')

    template = 'clients/_employee_confirm_delete_partial.html' if is_htmx(request) else 'clients/employee_confirm_delete.html'
    return render(request, template, {'obj': employee, 'page_title': f'Delete Employee — {employee.user.get_full_name()}'})


@role_required('admin', 'manager')
@require_http_methods(['GET'])
def employee_detail_view(request, pk):
    employee = get_object_or_404(Employee.objects.select_related('user', 'city', 'state'), pk=pk)
    return render(request, 'clients/employee_detail.html', {'obj': employee, 'page_title': employee.user.get_full_name()})


# ---------------------------------------------------------------------------
# Homeworker
# ---------------------------------------------------------------------------

@role_required('admin', 'manager', 'client')
@require_http_methods(['GET'])
def homeworker_list_view(request):
    homeworkers = Homeworker.objects.select_related('client', 'city', 'state').all()

    if request.user.is_client:
        homeworkers = homeworkers.filter(client__user=request.user)

    search = request.GET.get('search', '').strip()
    client_filter = request.GET.get('client', '')
    status_filter = request.GET.get('status', '')

    if search:
        homeworkers = homeworkers.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(client__company_name__icontains=search)
        )
    if client_filter:
        homeworkers = homeworkers.filter(client_id=client_filter)
    if status_filter == 'active':
        homeworkers = homeworkers.filter(is_active=True)
    elif status_filter == 'inactive':
        homeworkers = homeworkers.filter(is_active=False)

    context = {
        'homeworkers': homeworkers,
        'search': search,
        'clients': Client.objects.filter(is_active=True),
        'selected_client': client_filter,
        'selected_status': status_filter,
        'page_title': 'Homeworkers',
    }
    if is_htmx(request):
        return render(request, 'clients/_homeworker_list_table.html', context)
    return render(request, 'clients/homeworker_list.html', context)


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def homeworker_create_view(request):
    if request.method == 'POST':
        form = HomeworkerForm(request.POST, user=request.user)
        if form.is_valid():
            homeworker = form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Homeworker {homeworker.name} created.', status=204, extra_events={'homeworker-saved': True})
            messages.success(request, f'Homeworker {homeworker.name} created successfully.')
            return redirect('clients:homeworker_list')
    else:
        form = HomeworkerForm(user=request.user)

    template = 'clients/_homeworker_form_partial.html' if is_htmx(request) else 'clients/homeworker_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Add Homeworker'})


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def homeworker_update_view(request, pk):
    homeworker = get_object_or_404(Homeworker, pk=pk)

    if request.user.is_client and homeworker.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this homeworker.')

    if request.method == 'POST':
        form = HomeworkerForm(request.POST, instance=homeworker, user=request.user)
        if form.is_valid():
            form.save()
            if is_htmx(request):
                return _hx_toast('success', f'Homeworker {homeworker.name} updated.', status=204, extra_events={'homeworker-saved': True})
            messages.success(request, f'Homeworker {homeworker.name} updated successfully.')
            return redirect('clients:homeworker_list')
    else:
        form = HomeworkerForm(instance=homeworker, user=request.user)

    template = 'clients/_homeworker_form_partial.html' if is_htmx(request) else 'clients/homeworker_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': homeworker, 'page_title': f'Edit Homeworker — {homeworker.name}'})


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def homeworker_delete_view(request, pk):
    homeworker = get_object_or_404(Homeworker, pk=pk)

    if request.user.is_client and homeworker.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this homeworker.')

    if request.method == 'POST':
        name = homeworker.name
        homeworker.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Homeworker {name} deleted.', status=204, extra_events={'homeworker-saved': True})
        messages.success(request, f'Homeworker {name} deleted successfully.')
        return redirect('clients:homeworker_list')

    template = 'clients/_homeworker_confirm_delete_partial.html' if is_htmx(request) else 'clients/homeworker_confirm_delete.html'
    return render(request, template, {'obj': homeworker, 'page_title': f'Delete Homeworker — {homeworker.name}'})


@role_required('admin', 'manager', 'client')
@require_http_methods(['GET'])
def homeworker_detail_view(request, pk):
    homeworker = get_object_or_404(Homeworker.objects.select_related('client', 'city', 'state'), pk=pk)

    if request.user.is_client and homeworker.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this homeworker.')

    return render(request, 'clients/homeworker_detail.html', {'obj': homeworker, 'page_title': homeworker.name})
