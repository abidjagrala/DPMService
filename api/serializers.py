from rest_framework import serializers

from accounts.models import User
from assets.models import Asset, AssetAssignment
from clients.models import Client, Employee, Homeworker
from masters.models import AssetType, City, ServiceType, State, TransportType
from network.models import IPAddress, Subnet
from tickets.models import ServiceTicket, TicketComment, TicketHistory


# ---------------------------------------------------------------------------
# Masters
# ---------------------------------------------------------------------------

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name']


class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name', 'state', 'state_name']


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'description']


class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = ['id', 'name', 'description']


class TransportTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportType
        fields = ['id', 'name', 'description']


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'is_active']
        read_only_fields = ['id']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

class ClientSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True, default='')
    state_name = serializers.CharField(source='state.name', read_only=True, default='')

    class Meta:
        model = Client
        fields = [
            'id', 'user', 'company_name', 'contact_person', 'email', 'phone', 'alt_phone',
            'address', 'city', 'city_name', 'state', 'state_name', 'pincode',
            'gst_number', 'pan_number', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class EmployeeSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True, default='')

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_email', 'full_name', 'employee_id',
            'department', 'designation', 'phone', 'city', 'city_name',
            'address', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

class AssetAssignmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.company_name', read_only=True, default='')
    homeworker_name = serializers.CharField(source='homeworker.name', read_only=True, default='')
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True, default='')

    class Meta:
        model = AssetAssignment
        fields = [
            'id', 'asset', 'client', 'client_name', 'homeworker', 'homeworker_name',
            'assigned_by', 'assigned_by_name', 'assigned_date', 'return_date', 'notes',
        ]
        read_only_fields = ['id', 'assigned_date']


class AssetSerializer(serializers.ModelSerializer):
    asset_type_name = serializers.CharField(source='asset_type.name', read_only=True)
    client_name = serializers.CharField(source='client.company_name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'asset_tag', 'serial_number', 'asset_type', 'asset_type_name',
            'brand_model', 'status', 'status_display', 'ip_address', 'mac_address',
            'client', 'client_name', 'purchase_date',
            'warranty_expiry', 'notes', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

class SubnetSerializer(serializers.ModelSerializer):
    ip_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Subnet
        fields = ['id', 'name', 'cidr', 'gateway', 'description', 'ip_count', 'is_active']


class IPAddressSerializer(serializers.ModelSerializer):
    subnet_name = serializers.CharField(source='subnet.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = IPAddress
        fields = [
            'id', 'ip_address', 'subnet', 'subnet_name', 'hostname',
            'status', 'status_display', 'notes', 'is_active',
        ]
        read_only_fields = ['id']


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

class TicketCommentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, default='')

    class Meta:
        model = TicketComment
        fields = ['id', 'ticket', 'comment', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class TicketHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True, default='')

    class Meta:
        model = TicketHistory
        fields = [
            'id', 'ticket', 'field_changed', 'old_value', 'new_value',
            'changed_by', 'changed_by_name', 'changed_at',
        ]
        read_only_fields = ['id', 'changed_at']


class ServiceTicketSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    asset_tag = serializers.CharField(source='asset.asset_tag', read_only=True, default='')
    assigned_to_name = serializers.CharField(source='assigned_to.user.get_full_name', read_only=True, default='')
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    transport_type_name = serializers.CharField(source='transport_type.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = ServiceTicket
        fields = [
            'id', 'ticket_number',
            'service_type', 'service_type_name', 'client', 'client_name',
            'asset', 'asset_tag', 'assigned_to', 'assigned_to_name',
            'priority', 'priority_display', 'status', 'status_display',
            'subject', 'description', 'scheduled_date', 'completed_date',
            'address', 'contact_person', 'contact_phone',
            'transport_type', 'transport_type_name', 'tracking_url',
            'notes', 'created_by', 'is_overdue', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'ticket_number', 'created_at', 'updated_at']
