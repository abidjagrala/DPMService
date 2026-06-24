import ipaddress

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from clients.models import Client
from masters.models import City, State


class Subnet(models.Model):
    """Network subnet/VLAN block."""

    name = models.CharField(
        _('name'),
        max_length=100,
    )
    cidr = models.CharField(
        _('CIDR notation'),
        max_length=18,
        unique=True,
        help_text=_('e.g. 192.168.1.0/24'),
    )
    gateway = models.GenericIPAddressField(
        _('gateway'),
        blank=True,
        null=True,
    )
    vlan_id = models.PositiveIntegerField(
        _('VLAN ID'),
        blank=True,
        null=True,
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        related_name='subnets',
        verbose_name=_('client'),
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('subnet')
        verbose_name_plural = _('subnets')
        ordering = ['cidr']

    def __str__(self) -> str:
        label = f'{self.name} ({self.cidr})'
        if self.vlan_id:
            label += f' [VLAN {self.vlan_id}]'
        return label

    def clean(self):
        try:
            network = ipaddress.ip_network(self.cidr, strict=False)
            self.cidr = str(network)
        except ValueError:
            raise ValidationError({'cidr': _('Enter a valid CIDR notation.')})

    @property
    def total_ips(self) -> int:
        network = ipaddress.ip_network(self.cidr, strict=False)
        return network.num_addresses


class IPAddress(models.Model):
    """Individual IP address within a subnet."""

    class Status(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        ASSIGNED = 'assigned', _('Assigned')
        RESERVED = 'reserved', _('Reserved')
        UNAVAILABLE = 'unavailable', _('Unavailable')

    subnet = models.ForeignKey(
        Subnet,
        on_delete=models.CASCADE,
        related_name='ip_addresses',
        verbose_name=_('subnet'),
    )
    ip_address = models.GenericIPAddressField(
        _('IP address'),
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    hostname = models.CharField(
        _('hostname'),
        max_length=200,
        blank=True,
        default='',
    )
    mac_address = models.CharField(
        _('MAC address'),
        max_length=17,
        blank=True,
        default='',
        help_text=_('Format: AA:BB:CC:DD:EE:FF'),
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        related_name='ip_addresses',
        verbose_name=_('client'),
        null=True,
        blank=True,
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default='',
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('IP address')
        verbose_name_plural = _('IP addresses')
        ordering = ['subnet', 'ip_address']
        unique_together = [('subnet', 'ip_address')]

    def __str__(self) -> str:
        return f'{self.ip_address} ({self.subnet.name})'


class NetworkDevice(models.Model):
    """Network device (router, switch, firewall, AP)."""

    class DeviceType(models.TextChoices):
        ROUTER = 'router', _('Router')
        SWITCH = 'switch', _('Switch')
        FIREWALL = 'firewall', _('Firewall')
        ACCESS_POINT = 'access_point', _('Access Point')
        OTHER = 'other', _('Other')

    name = models.CharField(
        _('device name'),
        max_length=150,
    )
    device_type = models.CharField(
        _('device type'),
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.OTHER,
    )
    ip_address = models.CharField(
        _('IP address'),
        max_length=45,
    )
    subnet = models.CharField(
        _('subnet'),
        max_length=100,
        blank=True,
        default='',
    )
    mac_address = models.CharField(
        _('MAC address'),
        max_length=17,
        blank=True,
        default='',
    )
    brand = models.CharField(
        _('brand'),
        max_length=100,
        blank=True,
        default='',
    )
    model_name = models.CharField(
        _('model'),
        max_length=150,
        blank=True,
        default='',
    )
    serial_number = models.CharField(
        _('serial number'),
        max_length=100,
        blank=True,
        default='',
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        related_name='network_devices',
        verbose_name=_('client'),
        null=True,
        blank=True,
    )
    homeworker = models.ForeignKey(
        'clients.Homeworker',
        on_delete=models.SET_NULL,
        related_name='devices',
        verbose_name=_('homeworker'),
        null=True,
        blank=True,
    )
    location = models.CharField(
        _('location'),
        max_length=200,
        blank=True,
        default='',
    )
    username = models.CharField(
        _('username'),
        max_length=150,
        blank=True,
        default='',
    )
    password = models.CharField(
        _('password'),
        max_length=255,
        blank=True,
        default='',
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default='',
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('network device')
        verbose_name_plural = _('network devices')
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.name} ({self.ip_address})'
