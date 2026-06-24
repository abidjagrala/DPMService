from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from clients.models import Client


class DomainHosting(models.Model):
    """Domain or hosting service managed for a client."""

    class ServiceType(models.TextChoices):
        DOMAIN = 'domain', _('Domain')
        HOSTING = 'hosting', _('Hosting')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        EXPIRED = 'expired', _('Expired')
        SUSPENDED = 'suspended', _('Suspended')
        PENDING = 'pending', _('Pending')

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='domain_hosting_services',
        verbose_name=_('client'),
    )
    service_type = models.CharField(
        _('service type'),
        max_length=10,
        choices=ServiceType.choices,
    )
    service_name = models.CharField(
        _('service name'),
        max_length=255,
        help_text=_('e.g. example.com or hosting plan name'),
    )
    provider = models.CharField(
        _('provider / registrar'),
        max_length=200,
        blank=True,
        default='',
    )
    registration_date = models.DateField(
        _('registration date'),
    )
    expiry_date = models.DateField(
        _('expiry date'),
    )
    renewal_amount = models.DecimalField(
        _('renewal amount'),
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    gst_percent = models.DecimalField(
        _('GST %'),
        max_digits=5,
        decimal_places=2,
        default=18,
    )
    status = models.CharField(
        _('status'),
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    nameserver = models.CharField(
        _('nameserver'),
        max_length=255,
        blank=True,
        default='',
    )
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        blank=True,
        null=True,
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default='',
    )
    reminder_sent = models.BooleanField(
        _('expiry reminder sent'),
        default=False,
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('domain / hosting')
        verbose_name_plural = _('domains / hosting')
        ordering = ['-expiry_date']

    def __str__(self) -> str:
        return f'{self.get_service_type_display()}: {self.service_name}'

    @property
    def days_until_expiry(self) -> int:
        return (self.expiry_date - timezone.now().date()).days

    @property
    def is_expiring_soon(self) -> bool:
        return 0 < self.days_until_expiry <= 10

    @property
    def is_expired(self) -> bool:
        return self.expiry_date < timezone.now().date()

    @property
    def renewal_with_gst(self):
        gst = self.renewal_amount * self.gst_percent / 100
        return self.renewal_amount + gst


class DomainHostingInvoice(models.Model):
    """Invoice / payment record for a domain / hosting service."""

    service = models.ForeignKey(
        DomainHosting,
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name=_('service'),
    )
    invoice_number = models.CharField(
        _('invoice number'),
        max_length=50,
        blank=True,
        default='',
    )
    invoice_date = models.DateField(
        _('invoice date'),
    )
    amount = models.DecimalField(
        _('amount'),
        max_digits=12,
        decimal_places=2,
    )
    paid = models.BooleanField(_('paid'), default=False)
    paid_date = models.DateField(
        _('paid date'),
        blank=True,
        null=True,
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        default='',
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('invoice')
        verbose_name_plural = _('invoices')
        ordering = ['-invoice_date']

    def __str__(self) -> str:
        return f'{self.service.service_name} — {self.invoice_date}'
