from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from assets.models import Asset
from clients.models import Client, Employee
from masters.models import ServiceType, TransportType


class ServiceTicket(models.Model):
    """DPM service ticket for pickup, drop, or maintenance."""

    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')

    class Status(models.TextChoices):
        NEW = 'new', _('New')
        ASSIGNED = 'assigned', _('Assigned')
        IN_PROGRESS = 'in_progress', _('In Progress')
        ON_HOLD = 'on_hold', _('On Hold')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')

    ticket_number = models.CharField(
        _('ticket number'),
        max_length=20,
        unique=True,
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name=_('service type'),
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='service_tickets',
        verbose_name=_('client'),
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name='service_tickets',
        verbose_name=_('asset'),
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        related_name='service_tickets',
        verbose_name=_('assigned to'),
        null=True,
        blank=True,
    )
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    subject = models.CharField(
        _('subject'),
        max_length=200,
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
    )
    scheduled_date = models.DateField(
        _('scheduled date'),
        null=True,
        blank=True,
    )
    completed_date = models.DateTimeField(
        _('completed date'),
        null=True,
        blank=True,
    )
    address = models.TextField(
        _('address'),
        blank=True,
        default='',
    )
    contact_person = models.CharField(
        _('contact person'),
        max_length=150,
        blank=True,
        default='',
    )
    contact_phone = models.CharField(
        _('contact phone'),
        max_length=20,
        blank=True,
        default='',
    )
    transport_type = models.ForeignKey(
        TransportType,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name=_('transport type'),
        null=True,
        blank=True,
    )
    tracking_url = models.URLField(
        _('tracking URL'),
        max_length=500,
        blank=True,
        default='',
        help_text=_('Public tracking URL for the service status.'),
    )
    notes = models.TextField(
        _('internal notes'),
        blank=True,
        default='',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_tickets',
        verbose_name=_('created by'),
        null=True,
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('service ticket')
        verbose_name_plural = _('service tickets')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.ticket_number} — {self.subject}'

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self._generate_ticket_number()
        super().save(*args, **kwargs)

    def _generate_ticket_number(self) -> str:
        today = timezone.now()
        prefix = today.strftime('DPM%y%m')
        last_ticket = ServiceTicket.objects.filter(
            ticket_number__startswith=prefix
        ).order_by('-ticket_number').first()

        if last_ticket:
            seq = int(last_ticket.ticket_number[-4:]) + 1
        else:
            seq = 1
        return f'{prefix}{seq:04d}'

    @property
    def is_overdue(self) -> bool:
        if self.scheduled_date and self.status not in (self.Status.COMPLETED, self.Status.CANCELLED):
            return self.scheduled_date < timezone.now().date()
        return False


class TicketComment(models.Model):
    """Comment on a service ticket."""

    ticket = models.ForeignKey(
        ServiceTicket,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('ticket'),
    )
    comment = models.TextField(_('comment'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ticket_comments',
        verbose_name=_('created by'),
        null=True,
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('ticket comment')
        verbose_name_plural = _('ticket comments')
        ordering = ['created_at']

    def __str__(self) -> str:
        creator = self.created_by.get_full_name() if self.created_by else 'Unknown'
        return f'Comment on {self.ticket.ticket_number} by {creator}'


class TicketHistory(models.Model):
    """History of changes to a service ticket."""

    ticket = models.ForeignKey(
        ServiceTicket,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name=_('ticket'),
    )
    field_changed = models.CharField(_('field'), max_length=100)
    old_value = models.TextField(_('old value'), blank=True, default='')
    new_value = models.TextField(_('new value'), blank=True, default='')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ticket_history',
        verbose_name=_('changed by'),
        null=True,
    )
    changed_at = models.DateTimeField(_('changed at'), auto_now_add=True)

    class Meta:
        verbose_name = _('ticket history')
        verbose_name_plural = _('ticket histories')
        ordering = ['-changed_at']

    def __str__(self) -> str:
        return f'{self.ticket.ticket_number}: {self.field_changed}'
