from django.db import models
from django.utils.translation import gettext_lazy as _


class State(models.Model):
    """Indian state or union territory."""

    name = models.CharField(
        _('state name'),
        max_length=100,
        unique=True,
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('state')
        verbose_name_plural = _('states')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class City(models.Model):
    """City belonging to a state."""

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name='cities',
        verbose_name=_('state'),
    )
    name = models.CharField(
        _('city name'),
        max_length=100,
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('city')
        verbose_name_plural = _('cities')
        ordering = ['state', 'name']
        unique_together = [('state', 'name')]

    def __str__(self) -> str:
        return f'{self.name}, {self.state.name}'


class ServiceType(models.Model):
    """Type of DPM service offered."""

    name = models.CharField(
        _('service type name'),
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('service type')
        verbose_name_plural = _('service types')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class AssetType(models.Model):
    """Category of IT asset."""

    name = models.CharField(
        _('asset type name'),
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('asset type')
        verbose_name_plural = _('asset types')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class TransportType(models.Model):
    """Mode of transport for pickup/drop."""

    name = models.CharField(
        _('transport type name'),
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        _('description'),
        blank=True,
        default='',
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('transport type')
        verbose_name_plural = _('transport types')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name
