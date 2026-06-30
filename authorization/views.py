import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import (
    FieldPermissionForm, GroupForm, ModelPermissionBulkForm,
    ModulePermissionForm, RoleForm, UserRoleAssignmentForm,
)
from .models import (
    AuditLog, FieldPermission, Group, MenuPermission, MenuItem,
    ModelPermission, Module, ModulePermission, Role, UserRoleAssignment,
)
from .services.permission_engine import clear_user_permissions, clear_all_permissions

User = get_user_model()


def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _hx_toast(level, message, status=200, extra_events=None):
    payload = {'toast': {'level': level, 'message': str(message)}}
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


def _hx_redirect(url, level=None, message=None):
    response = HttpResponse(status=204)
    response['HX-Redirect'] = url
    if level and message:
        response['HX-Trigger'] = json.dumps({'toast': {'level': level, 'message': str(message)}})
    return response


def _admin_required(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return False
    return True


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def auth_dashboard(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    context = {
        'total_roles': Role.objects.count(),
        'total_groups': Group.objects.count(),
        'total_users_assigned': UserRoleAssignment.objects.filter(is_active=True).values('user').distinct().count(),
        'active_permissions': ModulePermission.objects.count() + ModelPermission.objects.count(),
        'recent_changes': AuditLog.objects.select_related('user').order_by('-timestamp')[:10],
        'roles': Role.objects.filter(is_active=True)[:5],
    }

    if _is_htmx(request):
        return render(request, 'authorization/partials/_dashboard_content.html', context)
    return render(request, 'authorization/dashboard.html', context)


# ---------------------------------------------------------------------------
# Group CRUD
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def group_list(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    search = request.GET.get('search', '').strip()
    groups = Group.objects.all()
    if search:
        groups = groups.filter(Q(name__icontains=search) | Q(description__icontains=search))

    context = {'groups': groups, 'search': search, 'total': groups.count()}

    if _is_htmx(request):
        return render(request, 'authorization/partials/_group_list_table.html', context)
    return render(request, 'authorization/group_list.html', context)


@csrf_protect
@require_http_methods(['GET', 'POST'])
def group_create(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            AuditLog.log(request.user, 'create', 'group', group, ip_address=_get_client_ip(request))
            if _is_htmx(request):
                return _hx_redirect('/authorization/groups/', 'success', f'Group "{group.name}" created.')
            messages.success(request, f'Group "{group.name}" created successfully.')
            return redirect('authorization:group_list')
    else:
        form = GroupForm()

    template = 'authorization/partials/_group_form_partial.html' if _is_htmx(request) else 'authorization/group_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Create Group'})


@csrf_protect
@require_http_methods(['GET', 'POST'])
def group_edit(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    group = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            old_data = {f: getattr(group, f) for f in ['name', 'description', 'is_active']}
            group = form.save()
            new_data = {f: getattr(group, f) for f in ['name', 'description', 'is_active']}
            changes = {k: {'old': old_data[k], 'new': new_data[k]} for k in old_data if old_data[k] != new_data[k]}
            AuditLog.log(request.user, 'update', 'group', group, changes=changes, ip_address=_get_client_ip(request))
            if _is_htmx(request):
                return _hx_redirect('/authorization/groups/', 'success', f'Group "{group.name}" updated.')
            messages.success(request, f'Group "{group.name}" updated successfully.')
            return redirect('authorization:group_list')
    else:
        form = GroupForm(instance=group)

    template = 'authorization/partials/_group_form_partial.html' if _is_htmx(request) else 'authorization/group_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'page_title': f'Edit {group.name}', 'group': group})


@csrf_protect
@require_http_methods(['GET', 'POST'])
def group_delete(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    group = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        name = group.name
        AuditLog.log(request.user, 'delete', 'group', group, ip_address=_get_client_ip(request))
        group.delete()
        if _is_htmx(request):
            return _hx_redirect('/authorization/groups/', 'success', f'Group "{name}" deleted.')
        messages.success(request, f'Group "{name}" deleted successfully.')
        return redirect('authorization:group_list')

    template = 'authorization/partials/_group_confirm_delete_partial.html' if _is_htmx(request) else 'authorization/group_confirm_delete.html'
    return render(request, template, {'group': group})


# ---------------------------------------------------------------------------
# Role CRUD
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def role_list(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    search = request.GET.get('search', '').strip()
    roles = Role.objects.select_related('group').all()
    if search:
        roles = roles.filter(Q(name__icontains=search) | Q(description__icontains=search))

    context = {'roles': roles, 'search': search, 'total': roles.count()}

    if _is_htmx(request):
        return render(request, 'authorization/partials/_role_list_table.html', context)
    return render(request, 'authorization/role_list.html', context)


@csrf_protect
@require_http_methods(['GET', 'POST'])
def role_create(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            AuditLog.log(request.user, 'create', 'role', role, ip_address=_get_client_ip(request))
            if _is_htmx(request):
                return _hx_redirect('/authorization/roles/', 'success', f'Role "{role.name}" created.')
            messages.success(request, f'Role "{role.name}" created successfully.')
            return redirect('authorization:role_list')
    else:
        form = RoleForm()

    template = 'authorization/partials/_role_form_partial.html' if _is_htmx(request) else 'authorization/role_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Create Role'})


@csrf_protect
@require_http_methods(['GET', 'POST'])
def role_edit(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role = get_object_or_404(Role, pk=pk)

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            old_data = {f: getattr(role, f) for f in ['name', 'description', 'is_active']}
            role = form.save()
            new_data = {f: getattr(role, f) for f in ['name', 'description', 'is_active']}
            changes = {k: {'old': old_data[k], 'new': new_data[k]} for k in old_data if old_data[k] != new_data[k]}
            AuditLog.log(request.user, 'update', 'role', role, changes=changes, ip_address=_get_client_ip(request))
            if _is_htmx(request):
                return _hx_redirect('/authorization/roles/', 'success', f'Role "{role.name}" updated.')
            messages.success(request, f'Role "{role.name}" updated successfully.')
            return redirect('authorization:role_list')
    else:
        form = RoleForm(instance=role)

    template = 'authorization/partials/_role_form_partial.html' if _is_htmx(request) else 'authorization/role_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'page_title': f'Edit {role.name}', 'role': role})


@csrf_protect
@require_http_methods(['GET', 'POST'])
def role_delete(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role = get_object_or_404(Role, pk=pk)

    if request.method == 'POST':
        name = role.name
        AuditLog.log(request.user, 'delete', 'role', role, ip_address=_get_client_ip(request))
        role.delete()
        if _is_htmx(request):
            return _hx_redirect('/authorization/roles/', 'success', f'Role "{name}" deleted.')
        messages.success(request, f'Role "{name}" deleted successfully.')
        return redirect('authorization:role_list')

    template = 'authorization/partials/_role_confirm_delete_partial.html' if _is_htmx(request) else 'authorization/role_confirm_delete.html'
    return render(request, template, {'role': role})


@csrf_protect
@require_http_methods(['POST'])
def role_clone(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role = get_object_or_404(Role, pk=pk)
    new_name = request.POST.get('name', f'{role.name} (Clone)')
    cloned = role.clone(new_name)
    AuditLog.log(request.user, 'clone', 'role', cloned, changes={'cloned_from': role.pk}, ip_address=_get_client_ip(request))
    clear_all_permissions()

    if _is_htmx(request):
        return _hx_redirect('/authorization/roles/', 'success', f'Role cloned as "{cloned.name}".')
    messages.success(request, f'Role cloned as "{cloned.name}".')
    return redirect('authorization:role_list')


@never_cache
@require_http_methods(['GET'])
def role_detail(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role = get_object_or_404(Role, pk=pk)
    assignments = UserRoleAssignment.objects.filter(role=role).select_related('user', 'group')
    module_perms = ModulePermission.objects.filter(role=role).select_related('module')
    model_perms = ModelPermission.objects.filter(role=role)

    context = {
        'role': role,
        'assignments': assignments,
        'module_perms': module_perms,
        'model_perms': model_perms,
    }
    return render(request, 'authorization/role_detail.html', context)


# ---------------------------------------------------------------------------
# Module Permissions
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def module_permission_matrix(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.GET.get('role', '')
    roles = Role.objects.filter(is_active=True).order_by('name')
    modules = Module.objects.filter(is_active=True).order_by('order')
    perm_labels = ['view', 'create', 'edit', 'delete', 'export', 'import', 'approve', 'assign']

    selected_role = None
    matrix = {}
    if role_id:
        selected_role = get_object_or_404(Role, pk=role_id)
        for mp in ModulePermission.objects.filter(role=selected_role).select_related('module'):
            matrix[mp.module.code] = mp.permissions

    context = {
        'roles': roles,
        'modules': modules,
        'perm_labels': perm_labels,
        'selected_role': selected_role,
        'matrix': matrix,
    }

    if _is_htmx(request):
        return render(request, 'authorization/partials/_module_perm_matrix.html', context)
    return render(request, 'authorization/module_perm_matrix.html', context)


@csrf_protect
@require_http_methods(['POST'])
def module_permission_save(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.POST.get('role')
    if not role_id:
        return _hx_toast('error', 'Role is required.', status=400)

    role = get_object_or_404(Role, pk=role_id)
    modules = Module.objects.filter(is_active=True)

    for module in modules:
        perms = {}
        for perm in ['view', 'create', 'edit', 'delete', 'export', 'import', 'approve', 'assign']:
            key = f'mod_{module.code}_{perm}'
            perms[perm] = key in request.POST

        mp, _ = ModulePermission.objects.update_or_create(
            role=role, module=module,
            defaults={'permissions': perms},
        )

    AuditLog.log(request.user, 'update', 'modulepermission', role, changes={'role': role.name}, ip_address=_get_client_ip(request))
    clear_all_permissions()

    return _hx_toast('success', f'Module permissions saved for {role.name}.', status=204, extra_events={'auth-saved': True})


# ---------------------------------------------------------------------------
# Model Permissions
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def model_permission_matrix(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.GET.get('role', '')
    roles = Role.objects.filter(is_active=True).order_by('name')
    models_list = [m for m in ModelPermission._meta.get_field('model').choices if m[0]]
    perm_labels = ['view', 'create', 'edit', 'delete', 'export', 'import', 'approve', 'assign']

    selected_role = None
    matrix = {}
    if role_id:
        selected_role = get_object_or_404(Role, pk=role_id)
        for mp in ModelPermission.objects.filter(role=selected_role):
            matrix[mp.model] = mp.permissions

    context = {
        'roles': roles,
        'models_list': models_list,
        'perm_labels': perm_labels,
        'selected_role': selected_role,
        'matrix': matrix,
    }

    if _is_htmx(request):
        return render(request, 'authorization/partials/_model_perm_matrix.html', context)
    return render(request, 'authorization/model_perm_matrix.html', context)


@csrf_protect
@require_http_methods(['POST'])
def model_permission_save(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.POST.get('role')
    if not role_id:
        return _hx_toast('error', 'Role is required.', status=400)

    role = get_object_or_404(Role, pk=role_id)
    models_list = [m[0] for m in ModelPermission._meta.get_field('model').choices if m[0]]

    for model_name in models_list:
        perms = {}
        for perm in ['view', 'create', 'edit', 'delete', 'export', 'import', 'approve', 'assign']:
            key = f'mdl_{model_name}_{perm}'
            perms[perm] = key in request.POST

        ModelPermission.objects.update_or_create(
            role=role, model=model_name,
            defaults={'permissions': perms},
        )

    AuditLog.log(request.user, 'update', 'modelpermission', role, changes={'role': role.name}, ip_address=_get_client_ip(request))
    clear_all_permissions()

    return _hx_toast('success', f'Model permissions saved for {role.name}.', status=204, extra_events={'auth-saved': True})


# ---------------------------------------------------------------------------
# Field Permissions
# ---------------------------------------------------------------------------

FIELD_MAP = {
    'serviceticket': [
        'ticket_number', 'service_type', 'client', 'asset', 'assigned_to',
        'priority', 'status', 'subject', 'description', 'scheduled_date',
        'completed_date', 'address', 'contact_person', 'contact_phone',
        'transport_type', 'tracking_url', 'notes', 'created_by',
    ],
    'client': [
        'company_name', 'contact_person', 'email', 'phone', 'alt_phone',
        'address', 'city', 'state', 'pincode', 'gst_number', 'pan_number', 'is_active',
    ],
    'employee': [
        'user', 'employee_id', 'designation', 'department', 'phone',
        'alt_phone', 'address', 'city', 'state', 'pincode', 'is_active',
    ],
    'asset': [
        'asset_tag', 'serial_number', 'asset_type', 'brand_model',
        'ip_address', 'mac_address', 'purchase_date', 'warranty_expiry',
        'status', 'client', 'homeworker', 'notes', 'is_active',
    ],
    'user': [
        'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff',
    ],
    'domainhosting': [
        'client', 'service_type', 'service_name', 'provider', 'registration_date',
        'expiry_date', 'renewal_amount', 'gst_percent', 'status', 'nameserver',
        'ip_address', 'notes', 'is_active',
    ],
}


@never_cache
@require_http_methods(['GET'])
def field_permission_matrix(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.GET.get('role', '')
    model = request.GET.get('model', '')

    roles = Role.objects.filter(is_active=True).order_by('name')
    model_choices = [(k, k.title()) for k in FIELD_MAP.keys()]

    selected_role = None
    fields = []
    field_perms = {}

    if model and model in FIELD_MAP:
        fields = FIELD_MAP[model]

    if role_id:
        selected_role = get_object_or_404(Role, pk=role_id)
        for fp in FieldPermission.objects.filter(role=selected_role, model=model):
            field_perms[fp.field_name] = fp.permission

    context = {
        'roles': roles,
        'model_choices': model_choices,
        'selected_role': selected_role,
        'selected_model': model,
        'fields': fields,
        'field_perms': field_perms,
        'permission_choices': [('hidden', 'Hidden'), ('readonly', 'Read Only'), ('editable', 'Editable')],
    }

    if _is_htmx(request):
        return render(request, 'authorization/partials/_field_perm_matrix.html', context)
    return render(request, 'authorization/field_perm_matrix.html', context)


@csrf_protect
@require_http_methods(['POST'])
def field_permission_save(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.POST.get('role')
    model = request.POST.get('model')

    if not role_id or not model:
        return _hx_toast('error', 'Role and model are required.', status=400)

    role = get_object_or_404(Role, pk=role_id)

    FieldPermission.objects.filter(role=role, model=model).delete()

    for key, value in request.POST.items():
        if key.startswith('fp_') and value in ('hidden', 'readonly', 'editable'):
            field_name = key[3:]
            FieldPermission.objects.create(
                role=role, model=model, field_name=field_name, permission=value,
            )

    AuditLog.log(request.user, 'update', 'fieldpermission', role, changes={'role': role.name, 'model': model}, ip_address=_get_client_ip(request))
    clear_all_permissions()

    return _hx_toast('success', f'Field permissions saved for {role.name} — {model}.', status=204, extra_events={'auth-saved': True})


# ---------------------------------------------------------------------------
# Menu Permissions
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def menu_permission_matrix(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.GET.get('role', '')
    roles = Role.objects.filter(is_active=True).order_by('name')
    menu_items = MenuItem.objects.filter(is_active=True).select_related('module', 'parent').order_by('module__order', 'order')

    selected_role = None
    menu_perms = {}

    if role_id:
        selected_role = get_object_or_404(Role, pk=role_id)
        for mp in MenuPermission.objects.filter(role=selected_role).select_related('menu_item'):
            menu_perms[mp.menu_item_id] = mp.is_visible

    context = {
        'roles': roles,
        'menu_items': menu_items,
        'selected_role': selected_role,
        'menu_perms': menu_perms,
    }

    if _is_htmx(request):
        return render(request, 'authorization/partials/_menu_perm_matrix.html', context)
    return render(request, 'authorization/menu_perm_matrix.html', context)


@csrf_protect
@require_http_methods(['POST'])
def menu_permission_save(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    role_id = request.POST.get('role')
    if not role_id:
        return _hx_toast('error', 'Role is required.', status=400)

    role = get_object_or_404(Role, pk=role_id)
    menu_items = MenuItem.objects.filter(is_active=True)

    for mi in menu_items:
        key = f'menu_{mi.pk}'
        is_visible = key in request.POST
        MenuPermission.objects.update_or_create(
            role=role, menu_item=mi,
            defaults={'is_visible': is_visible},
        )

    AuditLog.log(request.user, 'update', 'menupermission', role, changes={'role': role.name}, ip_address=_get_client_ip(request))
    clear_all_permissions()

    return _hx_toast('success', f'Menu permissions saved for {role.name}.', status=204, extra_events={'auth-saved': True})


# ---------------------------------------------------------------------------
# User Role Assignment
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def user_assignment_list(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    search = request.GET.get('search', '').strip()
    assignments = UserRoleAssignment.objects.select_related('user', 'role', 'group', 'assigned_by').all()
    if search:
        assignments = assignments.filter(
            Q(user__email__icontains=search) |
            Q(role__name__icontains=search)
        )

    context = {'assignments': assignments, 'search': search, 'total': assignments.count()}

    if _is_htmx(request):
        return render(request, 'authorization/partials/_user_assignment_table.html', context)
    return render(request, 'authorization/user_assignment_list.html', context)


@csrf_protect
@require_http_methods(['GET', 'POST'])
def user_assignment_create(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = UserRoleAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.assigned_by = request.user
            assignment.save()
            AuditLog.log(request.user, 'assign', 'userroleassignment', assignment,
                         changes={'user': str(assignment.user), 'role': str(assignment.role)},
                         ip_address=_get_client_ip(request))
            clear_user_permissions(assignment.user_id)
            if _is_htmx(request):
                return _hx_redirect('/authorization/assignments/', 'success', f'Role assigned to {assignment.user.email}.')
            messages.success(request, f'Role assigned to {assignment.user.email}.')
            return redirect('authorization:user_assignment_list')
    else:
        form = UserRoleAssignmentForm()

    template = 'authorization/partials/_user_assignment_form_partial.html' if _is_htmx(request) else 'authorization/user_assignment_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Assign Role'})


@csrf_protect
@require_http_methods(['GET', 'POST'])
def user_assignment_edit(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    assignment = get_object_or_404(UserRoleAssignment, pk=pk)

    if request.method == 'POST':
        form = UserRoleAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            old_user = assignment.user_id
            assignment = form.save()
            AuditLog.log(request.user, 'update', 'userroleassignment', assignment,
                         changes={'user': str(assignment.user), 'role': str(assignment.role)},
                         ip_address=_get_client_ip(request))
            clear_user_permissions(old_user)
            clear_user_permissions(assignment.user_id)
            if _is_htmx(request):
                return _hx_redirect('/authorization/assignments/', 'success', 'Assignment updated.')
            messages.success(request, 'Assignment updated successfully.')
            return redirect('authorization:user_assignment_list')
    else:
        form = UserRoleAssignmentForm(instance=assignment)

    template = 'authorization/partials/_user_assignment_form_partial.html' if _is_htmx(request) else 'authorization/user_assignment_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'page_title': 'Edit Assignment', 'assignment': assignment})


@csrf_protect
@require_http_methods(['GET', 'POST'])
def user_assignment_delete(request, pk):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    assignment = get_object_or_404(UserRoleAssignment, pk=pk)

    if request.method == 'POST':
        user_id = assignment.user_id
        AuditLog.log(request.user, 'revoke', 'userroleassignment', assignment,
                     changes={'user': str(assignment.user), 'role': str(assignment.role)},
                     ip_address=_get_client_ip(request))
        assignment.delete()
        clear_user_permissions(user_id)
        if _is_htmx(request):
            return _hx_redirect('/authorization/assignments/', 'success', 'Assignment revoked.')
        messages.success(request, 'Assignment revoked successfully.')
        return redirect('authorization:user_assignment_list')

    template = 'authorization/partials/_user_assignment_confirm_delete_partial.html' if _is_htmx(request) else 'authorization/user_assignment_confirm_delete.html'
    return render(request, template, {'assignment': assignment})


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

@never_cache
@require_http_methods(['GET'])
def audit_log_list(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    search = request.GET.get('search', '').strip()
    action_filter = request.GET.get('action', '')

    logs = AuditLog.objects.select_related('user').all()
    if search:
        logs = logs.filter(
            Q(object_repr__icontains=search) |
            Q(model_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    if action_filter:
        logs = logs.filter(action=action_filter)

    context = {
        'logs': logs[:100],
        'search': search,
        'action_filter': action_filter,
        'action_choices': AuditLog.ACTION_CHOICES,
    }

    if _is_htmx(request):
        return render(request, 'authorization/partials/_audit_log_table.html', context)
    return render(request, 'authorization/audit_log_list.html', context)


# ---------------------------------------------------------------------------
# Seed Default Data
# ---------------------------------------------------------------------------

@csrf_protect
@require_http_methods(['POST'])
def seed_defaults(request):
    if not _admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    modules_data = [
        ('dashboard', 'Dashboard', 1),
        ('clients', 'Clients', 2),
        ('employees', 'Employees', 3),
        ('homeworkers', 'Homeworkers', 4),
        ('assets', 'Assets', 5),
        ('devices', 'Devices', 6),
        ('tickets', 'Tickets', 7),
        ('domain_hosting', 'Domain & Hosting', 8),
        ('notifications', 'Notifications', 9),
        ('settings', 'Settings', 10),
        ('authorization', 'Authorization & Roles', 11),
    ]

    for code, name, order in modules_data:
        Module.objects.get_or_create(code=code, defaults={'name': name, 'order': order})

    menu_data = [
        ('dashboard', 'Dashboard', 'accounts:dashboard', '', None, 1),
        ('clients', 'Clients', 'clients:client_list', '', None, 1),
        ('employees', 'Employees', 'clients:employee_list', '', None, 2),
        ('homeworkers', 'Homeworkers', 'clients:homeworker_list', '', None, 3),
        ('assets', 'Assets', 'assets:asset_list', '', None, 1),
        ('devices', 'Devices', 'network:device_list', '', None, 1),
        ('tickets', 'Service Tickets', 'tickets:ticket_list', '', None, 1),
        ('domain_hosting', 'Domain & Hosting', 'hosting:hosting_list', '', None, 1),
        ('notifications', 'Notifications', 'notifications:notification_list', '', None, 1),
        ('settings', 'Settings', '', '', None, 1),
        ('authorization', 'Authorization & Roles', 'authorization:auth_dashboard', '', None, 1),
    ]

    for module_code, name, url_name, icon, parent, order in menu_data:
        module = Module.objects.filter(code=module_code).first()
        if module:
            MenuItem.objects.get_or_create(
                name=name, module=module,
                defaults={'url_name': url_name, 'icon': icon, 'order': order},
            )

    if _is_htmx(request):
        return _hx_toast('success', 'Default modules and menu items seeded.', status=204, extra_events={'auth-saved': True})
    messages.success(request, 'Default modules and menu items seeded.')
    return redirect('authorization:auth_dashboard')
