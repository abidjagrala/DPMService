from django.contrib import admin

from .models import (
    AuditLog, FieldPermission, Group, MenuPermission, MenuItem,
    ModelPermission, Module, ModulePermission, Role, UserRoleAssignment,
)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'is_active', 'created_at')
    list_filter = ('is_active', 'group')
    search_fields = ('name',)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'order', 'is_active')
    list_filter = ('is_active',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'url_name', 'parent', 'order', 'is_active')
    list_filter = ('module', 'is_active')


@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'module')
    list_filter = ('role', 'module')


@admin.register(ModelPermission)
class ModelPermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'model')
    list_filter = ('role',)


@admin.register(FieldPermission)
class FieldPermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'model', 'field_name', 'permission')
    list_filter = ('role', 'model', 'permission')


@admin.register(MenuPermission)
class MenuPermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'menu_item', 'is_visible')
    list_filter = ('role', 'is_visible')


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'group', 'is_active', 'assigned_at')
    list_filter = ('is_active', 'role')
    search_fields = ('user__email',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'timestamp')
    list_filter = ('action', 'model_name')
    search_fields = ('object_repr', 'user__email')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'object_repr', 'changes', 'ip_address', 'timestamp')
