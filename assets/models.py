from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from clients.models import Client, Homeworker
from masters.models import AssetType


class Asset(models.Model):
    """IT asset tracked by the system."""

    class Status(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        ASSIGNED = 'assigned', _('Assigned')
        IN_REPAIR = 'in_repair', _('In Repair')
        RETIRED = 'retired', _('Retired')
        LOST = 'lost', _('Lost')

    asset_tag = models.CharField(
        _('asset tag'),
        max_length=50,
        unique=True,
        blank=True,
        help_text=_('Unique identifier for the asset.'),
    )
    serial_number = models.CharField(
        _('serial number'),
        max_length=100,
        blank=True,
        default='',
    )
    asset_type = models.ForeignKey(
        AssetType,
        on_delete=models.PROTECT,
        related_name='assets',
        verbose_name=_('asset type'),
    )
    brand_model = models.CharField(
        _('brand/model'),
        max_length=200,
        default='',
    )
    purchase_date = models.DateField(
        _('purchase date'),
        null=True,
        blank=True,
    )
    warranty_expiry = models.DateField(
        _('warranty expiry'),
        null=True,
        blank=True,
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        related_name='assets',
        verbose_name=_('client'),
        null=True,
        blank=True,
    )
    homeworker = models.ForeignKey(
        Homeworker,
        on_delete=models.SET_NULL,
        related_name='assets',
        verbose_name=_('homeworker'),
        null=True,
        blank=True,
    )
    ip_address = models.CharField(
        _('IP address'),
        max_length=45,
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
    notes = models.TextField(
        _('notes'),
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
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('asset')
        verbose_name_plural = _('assets')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.asset_tag} — {self.brand_model}'

    def save(self, *args, **kwargs):
        if not self.asset_tag:
            self.asset_tag = self._generate_asset_tag()
        super().save(*args, **kwargs)

    def _generate_asset_tag(self) -> str:
        last = Asset.objects.filter(
            asset_tag__startswith='AST-'
        ).order_by('-asset_tag').values_list('asset_tag', flat=True).first()

        if last:
            seq = int(last.split('-')[1]) + 1
        else:
            seq = 100001
        return f'AST-{seq:06d}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.status == self.Status.ASSIGNED and not self.homeworker:
            raise ValidationError({'homeworker': _('Homeworker is required when status is Assigned.')})

    @property
    def holder_name(self) -> str:
        if self.client:
            return self.client.company_name
        if self.homeworker:
            return self.homeworker.name
        return '—'


class AssetAssignment(models.Model):
    """History of asset assignments."""

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name=_('asset'),
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        related_name='asset_assignments',
        verbose_name=_('client'),
        null=True,
        blank=True,
    )
    homeworker = models.ForeignKey(
        Homeworker,
        on_delete=models.SET_NULL,
        related_name='asset_assignments',
        verbose_name=_('assigned to homeworker'),
        null=True,
        blank=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='asset_assignments_made',
        verbose_name=_('assigned by'),
        null=True,
    )
    assigned_date = models.DateTimeField(_('assigned date'), auto_now_add=True)
    return_date = models.DateTimeField(
        _('return date'),
        null=True,
        blank=True,
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default='',
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('asset assignment')
        verbose_name_plural = _('asset assignments')
        ordering = ['-assigned_date']

    def __str__(self) -> str:
        target = self.client or self.homeworker or 'Unassigned'
        return f'{self.asset.asset_tag} → {target}'
