from django.db.models import Count, Sum
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from accounts.models import User
from assets.models import Asset, AssetAssignment
from clients.models import Client, Employee
from masters.models import AssetType, City, ServiceType, State, TransportType
from network.models import IPAddress, Subnet
from tickets.models import ServiceTicket, TicketComment, TicketHistory

from .serializers import (
    AssetAssignmentSerializer,
    AssetSerializer,
    AssetTypeSerializer,
    CitySerializer,
    ClientSerializer,
    EmployeeSerializer,
    IPAddressSerializer,
    ServiceTicketSerializer,
    ServiceTypeSerializer,
    StateSerializer,
    SubnetSerializer,
    TicketCommentSerializer,
    TicketHistorySerializer,
    TransportTypeSerializer,
    UserCreateSerializer,
    UserSerializer,
)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_admin or request.user.is_manager or request.user.is_superuser
        )


class IsStaffOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_admin or request.user.is_manager or
            request.user.is_staff or request.user.is_superuser
        )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_token_view(request):
    """Exchange credentials for an auth token."""
    email = request.data.get('email')
    password = request.data.get('password')
    if not email or not password:
        return Response({'error': 'Email and password required.'}, status=400)

    user = User.objects.filter(email=email).first()
    if user is None or not user.check_password(password):
        return Response({'error': 'Invalid credentials.'}, status=401)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user': UserSerializer(user).data,
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_user_me_view(request):
    """Return the current authenticated user."""
    return Response(UserSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Masters ViewSets
# ---------------------------------------------------------------------------

class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [IsStaffOrAbove]


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.select_related('state').all()
    serializer_class = CitySerializer
    permission_classes = [IsStaffOrAbove]


class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsStaffOrAbove]


class AssetTypeViewSet(viewsets.ModelViewSet):
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer
    permission_classes = [IsStaffOrAbove]


class TransportTypeViewSet(viewsets.ModelViewSet):
    queryset = TransportType.objects.all()
    serializer_class = TransportTypeSerializer
    permission_classes = [IsStaffOrAbove]


# ---------------------------------------------------------------------------
# Accounts ViewSets
# ---------------------------------------------------------------------------

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrManager]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


# ---------------------------------------------------------------------------
# Clients ViewSets
# ---------------------------------------------------------------------------

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.select_related('city', 'state').all()
    serializer_class = ClientSerializer
    permission_classes = [IsAdminOrManager]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(company_name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(email__icontains=search)
            )
        return qs


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related('user', 'city', 'state').all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAdminOrManager]


# ---------------------------------------------------------------------------
# Assets ViewSets
# ---------------------------------------------------------------------------

class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related('asset_type', 'client', 'employee__user').all()
    serializer_class = AssetSerializer
    permission_classes = [IsStaffOrAbove]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(asset_tag__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(brand_model__icontains=search)
            )
        return qs

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        asset = self.get_object()
        assignments = asset.assignments.select_related('client', 'employee__user', 'assigned_by')
        serializer = AssetAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)


class AssetAssignmentViewSet(viewsets.ModelViewSet):
    queryset = AssetAssignment.objects.select_related('asset', 'client', 'employee__user', 'assigned_by').all()
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsAdminOrManager]


# ---------------------------------------------------------------------------
# Network ViewSets
# ---------------------------------------------------------------------------

class SubnetViewSet(viewsets.ModelViewSet):
    queryset = Subnet.objects.annotate(
        ip_count=Count('ip_addresses')
    ).all()
    serializer_class = SubnetSerializer
    permission_classes = [IsStaffOrAbove]


class IPAddressViewSet(viewsets.ModelViewSet):
    queryset = IPAddress.objects.select_related('subnet').all()
    serializer_class = IPAddressSerializer
    permission_classes = [IsStaffOrAbove]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


# ---------------------------------------------------------------------------
# Tickets ViewSets
# ---------------------------------------------------------------------------

class ServiceTicketViewSet(viewsets.ModelViewSet):
    queryset = ServiceTicket.objects.select_related(
        'service_type', 'client', 'asset', 'assigned_to__user', 'created_by'
    ).all()
    serializer_class = ServiceTicketSerializer
    permission_classes = [IsStaffOrAbove]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        priority_filter = self.request.query_params.get('priority')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if priority_filter:
            qs = qs.filter(priority=priority_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        comments = ticket.comments.select_related('created_by')
        serializer = TicketCommentSerializer(comments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        ticket = self.get_object()
        history = ticket.history.select_related('changed_by')
        serializer = TicketHistorySerializer(history, many=True)
        return Response(serializer.data)


class TicketCommentViewSet(viewsets.ModelViewSet):
    queryset = TicketComment.objects.select_related('created_by', 'ticket').all()
    serializer_class = TicketCommentSerializer
    permission_classes = [IsStaffOrAbove]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------------------------------------------------------------------
# Dashboard Summary
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsStaffOrAbove])
def api_dashboard_view(request):
    """API dashboard with summary counts."""
    return Response({
        'assets': {
            'total': Asset.objects.count(),
            'by_status': dict(
                Asset.objects.values_list('status')
                .annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
        },
        'tickets': {
            'total': ServiceTicket.objects.count(),
            'by_status': dict(
                ServiceTicket.objects.values_list('status')
                .annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
        },
        'clients': {
            'total': Client.objects.count(),
            'active': Client.objects.filter(is_active=True).count(),
        },
    })
