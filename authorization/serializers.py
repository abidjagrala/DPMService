from rest_framework import serializers

from .models import (
    AuditLog, FieldPermission, Group, MenuPermission, MenuItem,
    ModelPermission, Module, ModulePermission, Role, UserRoleAssignment,
)


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoleSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, default='')

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'group', 'group_name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoleDetailSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, default='')
    module_permissions = serializers.SerializerMethodField()
    model_permissions = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'group', 'group_name', 'is_active',
                  'module_permissions', 'model_permissions', 'user_count', 'created_at', 'updated_at']

    def get_module_permissions(self, obj):
        return ModulePermissionSerializer(obj.module_permissions.all(), many=True).data

    def get_model_permissions(self, obj):
        return ModelPermissionSerializer(obj.model_permissions.all(), many=True).data

    def get_user_count(self, obj):
        return obj.user_assignments.filter(is_active=True).count()


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'code', 'name', 'description', 'is_active', 'order']


class ModulePermissionSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)

    class Meta:
        model = ModulePermission
        fields = ['id', 'role', 'role_name', 'module', 'module_name', 'permissions']


class ModelPermissionSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = ModelPermission
        fields = ['id', 'role', 'role_name', 'model', 'permissions']


class FieldPermissionSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = FieldPermission
        fields = ['id', 'role', 'role_name', 'model', 'field_name', 'permission']


class MenuItemSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'url_name', 'module', 'module_name', 'parent', 'order', 'is_active']


class MenuPermissionSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)

    class Meta:
        model = MenuPermission
        fields = ['id', 'role', 'role_name', 'menu_item', 'menu_item_name', 'is_visible']


class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    role_name = serializers.CharField(source='role.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, default='')
    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = UserRoleAssignment
        fields = ['id', 'user', 'user_email', 'user_name', 'role', 'role_name',
                  'group', 'group_name', 'is_active', 'assigned_at', 'assigned_by', 'assigned_by_name']
        read_only_fields = ['id', 'assigned_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else ''

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.get_full_name() if obj.assigned_by else ''


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_email', 'action', 'model_name', 'object_id',
                  'object_repr', 'changes', 'ip_address', 'timestamp']
        read_only_fields = ['id', 'timestamp']
