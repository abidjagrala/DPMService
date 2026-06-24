from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages

CACHE_TTL = 300


def _cache_key(user_id):
    return f'auth_perms_{user_id}'


def get_user_permissions(user):
    if user.is_superuser:
        return {
            'modules': {m: {p: True for p in ['view', 'create', 'edit', 'delete', 'export', 'import', 'approve', 'assign']}
                        for m in ['dashboard', 'clients', 'employees', 'homeworkers', 'assets', 'devices',
                                  'tickets', 'domain_hosting', 'notifications', 'settings', 'authorization']},
            'models': {m: {p: True for p in ['view', 'create', 'edit', 'delete', 'export', 'import', 'approve', 'assign']}
                       for m in ['client', 'employee', 'homeworker', 'asset', 'assetassignment', 'subnet',
                                 'ipaddress', 'networkdevice', 'serviceticket', 'ticketcomment', 'tickethistory',
                                 'domainhosting', 'servicetype', 'assettype', 'state', 'city', 'user', 'group', 'role']},
            'fields': {},
            'menus': {},
        }

    key = _cache_key(user.pk)
    cached = cache.get(key)
    if cached:
        return cached

    from authorization.models import UserRoleAssignment, ModulePermission, ModelPermission, FieldPermission, MenuPermission

    assignments = UserRoleAssignment.objects.filter(
        user=user, is_active=True
    ).select_related('role')

    roles = [a.role for a in assignments]

    module_perms = {}
    for mp in ModulePermission.objects.filter(role__in=roles).select_related('module'):
        code = mp.module.code
        if code not in module_perms:
            module_perms[code] = {}
        for perm, val in mp.permissions.items():
            if val:
                module_perms[code][perm] = True

    model_perms = {}
    for mp in ModelPermission.objects.filter(role__in=roles):
        model = mp.model
        if model not in model_perms:
            model_perms[model] = {}
        for perm, val in mp.permissions.items():
            if val:
                model_perms[model][perm] = True

    field_perms = {}
    for fp in FieldPermission.objects.filter(role__in=roles):
        key_tuple = (fp.model, fp.field_name)
        if key_tuple not in field_perms:
            field_perms[key_tuple] = fp.permission
        elif fp.permission == 'hidden':
            field_perms[key_tuple] = 'hidden'

    menu_perms = {}
    for mp in MenuPermission.objects.filter(role__in=roles).select_related('menu_item'):
        menu_id = mp.menu_item_id
        if menu_id not in menu_perms:
            menu_perms[menu_id] = mp.is_visible
        else:
            menu_perms[menu_id] = menu_perms[menu_id] or mp.is_visible

    result = {
        'modules': module_perms,
        'models': model_perms,
        'fields': field_perms,
        'menus': menu_perms,
    }

    cache.set(key, result, CACHE_TTL)
    return result


def clear_user_permissions(user_id):
    cache.delete(_cache_key(user_id))


def clear_all_permissions():
    cache.clear()


def has_module_permission(user, module_code, perm='view'):
    perms = get_user_permissions(user)
    return perms['modules'].get(module_code, {}).get(perm, False)


def has_model_permission(user, model_name, perm='view'):
    perms = get_user_permissions(user)
    return perms['models'].get(model_name, {}).get(perm, False)


def get_field_permission(user, model_name, field_name):
    perms = get_user_permissions(user)
    return perms['fields'].get((model_name, field_name), 'editable')


def is_menu_visible(user, menu_item_id):
    perms = get_user_permissions(user)
    return perms['menus'].get(menu_item_id, True)


def has_any_permission(user):
    if user.is_superuser:
        return True
    from authorization.models import UserRoleAssignment
    return UserRoleAssignment.objects.filter(user=user, is_active=True).exists()


def module_required(module_code, perm='view'):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if not has_module_permission(request.user, module_code, perm):
                if request.headers.get('HX-Request') == 'true':
                    return HttpResponseForbidden('Access denied.')
                messages.error(request, f'You do not have permission to access this module.')
                return redirect('accounts:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def model_required(model_name, perm='view'):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if not has_model_permission(request.user, model_name, perm):
                if request.headers.get('HX-Request') == 'true':
                    return HttpResponseForbidden('Access denied.')
                messages.error(request, f'You do not have permission for this action.')
                return redirect('accounts:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
