from django import template
from authorization.services.permission_engine import (
    has_module_permission,
    has_model_permission,
    get_field_permission,
    is_menu_visible,
    has_any_permission,
)

register = template.Library()


@register.simple_tag
def has_module_perm(user, module_code, perm='view'):
    return has_module_permission(user, module_code, perm)


@register.simple_tag
def has_model_perm(user, model_name, perm='view'):
    return has_model_permission(user, model_name, perm)


@register.simple_tag
def field_perm(user, model_name, field_name):
    return get_field_permission(user, model_name, field_name)


@register.simple_tag
def menu_visible(user, menu_item_id):
    return is_menu_visible(user, menu_item_id)


@register.simple_tag
def has_dynamic_perms(user):
    return has_any_permission(user)


@register.filter
def has_module_perm_filter(user, module_code):
    return has_module_permission(user, module_code, 'view')


@register.filter
def has_model_perm_filter(user, model_perm_str):
    parts = model_perm_str.split(':')
    if len(parts) == 2:
        return has_model_permission(user, parts[0], parts[1])
    return False


@register.filter
def can_edit_field(user, field_perm_str):
    parts = field_perm_str.split(':')
    if len(parts) == 3:
        perm = get_field_permission(user, parts[0], parts[1])
        return perm == parts[2]
    return True


@register.filter
def is_field_visible(user, field_perm_str):
    parts = field_perm_str.split(':')
    if len(parts) == 2:
        perm = get_field_permission(user, parts[0], parts[1])
        return perm != 'hidden'
    return True


@register.filter
def is_field_readonly(user, field_perm_str):
    parts = field_perm_str.split(':')
    if len(parts) == 2:
        perm = get_field_permission(user, parts[0], parts[1])
        return perm == 'readonly'
    return False


@register.filter
def dict_get(d, key):
    """Get a value from a dictionary: {{ my_dict|dict_get:key }}"""
    if isinstance(d, dict):
        return d.get(key)
    return None


@register.filter
def dict_get_bool(d, key):
    """Get a boolean value from a dictionary: {{ my_dict|dict_get_bool:key }}"""
    if isinstance(d, dict):
        val = d.get(key, False)
        return bool(val)
    return False
