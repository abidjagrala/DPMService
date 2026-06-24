from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AuditLog, Group, MenuPermission, ModelPermission, Module, ModulePermission, Role, UserRoleAssignment
from .serializers import (
    AuditLogSerializer, GroupSerializer, MenuPermissionSerializer,
    ModelPermissionSerializer, ModulePermissionSerializer,
    ModuleSerializer, RoleDetailSerializer, RoleSerializer,
    UserRoleAssignmentSerializer,
)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.select_related('group').all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RoleDetailSerializer
        return RoleSerializer


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Module.objects.filter(is_active=True)
    serializer_class = ModuleSerializer
    permission_classes = [IsAdminUser]


class ModulePermissionViewSet(viewsets.ModelViewSet):
    queryset = ModulePermission.objects.select_related('role', 'module').all()
    serializer_class = ModulePermissionSerializer
    permission_classes = [IsAdminUser]


class ModelPermissionViewSet(viewsets.ModelViewSet):
    queryset = ModelPermission.objects.select_related('role').all()
    serializer_class = ModelPermissionSerializer
    permission_classes = [IsAdminUser]


class MenuPermissionViewSet(viewsets.ModelViewSet):
    queryset = MenuPermission.objects.select_related('role', 'menu_item').all()
    serializer_class = MenuPermissionSerializer
    permission_classes = [IsAdminUser]


class UserRoleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = UserRoleAssignment.objects.select_related('user', 'role', 'group', 'assigned_by').all()
    serializer_class = UserRoleAssignmentSerializer
    permission_classes = [IsAdminUser]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]


@api_view(['POST'])
@permission_classes([IsAdminUser])
def api_role_clone_view(request, pk):
    role = Role.objects.filter(pk=pk).first()
    if not role:
        return Response({'error': 'Role not found.'}, status=404)

    new_name = request.data.get('name', f'{role.name} (Clone)')
    cloned = role.clone(new_name)
    AuditLog.log(request.user, 'clone', 'role', cloned, changes={'cloned_from': role.pk})

    return Response(RoleSerializer(cloned).data, status=201)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def api_seed_view(request):
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

    return Response({'status': 'ok', 'message': 'Modules seeded.'})
