from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from masters.models import City, State


class Client(models.Model):
    """Business client using DPM services."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_profile',
        verbose_name=_('user'),
        null=True,
        blank=True,
    )
    company_name = models.CharField(
        _('company name'),
        max_length=200,
    )
    contact_person = models.CharField(
        _('contact person'),
        max_length=150,
    )
    email = models.EmailField(
        _('email address'),
        unique=True,
    )
    phone = models.CharField(
        _('phone number'),
        max_length=20,
    )
    alt_phone = models.CharField(
        _('alternate phone'),
        max_length=20,
        blank=True,
        default='',
    )
    address = models.TextField(
        _('address'),
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='clients',
        verbose_name=_('city'),
    )
    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        related_name='clients',
        verbose_name=_('state'),
    )
    pincode = models.CharField(
        _('pincode'),
        max_length=10,
    )
    gst_number = models.CharField(
        _('GST number'),
        max_length=20,
        blank=True,
        default='',
    )
    pan_number = models.CharField(
        _('PAN number'),
        max_length=20,
        blank=True,
        default='',
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('client')
        verbose_name_plural = _('clients')
        ordering = ['company_name']

    def __str__(self) -> str:
        return self.company_name


class Employee(models.Model):
    """ARWASYS employee handling DPM services."""

    class Department(models.TextChoices):
        OPERATIONS = 'operations', _('Operations')
        TECHNICAL = 'technical', _('Technical')
        ADMINISTRATION = 'administration', _('Administration')
        LOGISTICS = 'logistics', _('Logistics')
        SUPPORT = 'support', _('Support')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        verbose_name=_('user'),
    )
    employee_id = models.CharField(
        _('employee ID'),
        max_length=20,
        unique=True,
        blank=True,
    )
    designation = models.CharField(
        _('designation'),
        max_length=100,
    )
    department = models.CharField(
        _('department'),
        max_length=20,
        choices=Department.choices,
        default=Department.OPERATIONS,
    )
    phone = models.CharField(
        _('phone number'),
        max_length=20,
    )
    alt_phone = models.CharField(
        _('alternate phone'),
        max_length=20,
        blank=True,
        default='',
    )
    address = models.TextField(
        _('address'),
        blank=True,
        default='',
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='employees',
        verbose_name=_('city'),
        null=True,
        blank=True,
    )
    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        related_name='employees',
        verbose_name=_('state'),
        null=True,
        blank=True,
    )
    pincode = models.CharField(
        _('pincode'),
        max_length=10,
        blank=True,
        default='',
    )
    employee_photo = models.ImageField(
        _('employee photo'),
        upload_to='employees/photos/',
        blank=True,
        null=True,
    )
    aadhar_card = models.FileField(
        _('Aadhar card'),
        upload_to='employees/aadhar/',
        blank=True,
        null=True,
    )
    joining_date = models.DateField(
        _('joining date'),
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('employee')
        verbose_name_plural = _('employees')
        ordering = ['employee_id']

    def __str__(self) -> str:
        return f'{self.user.get_full_name()} ({self.employee_id})'

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self._generate_employee_id()
        super().save(*args, **kwargs)

    def _generate_employee_id(self) -> str:
        last = Employee.objects.filter(
            employee_id__startswith='EMP-'
        ).order_by('-employee_id').values_list('employee_id', flat=True).first()

        if last:
            seq = int(last.split('-')[1]) + 1
        else:
            seq = 1001
        return f'EMP-{seq:04d}'


class Homeworker(models.Model):
    """Client's employee who works from home — receives devices."""

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='homeworkers',
        verbose_name=_('client'),
    )
    name = models.CharField(
        _('name'),
        max_length=150,
    )
    email = models.EmailField(
        _('email address'),
        blank=True,
        default='',
    )
    phone = models.CharField(
        _('phone number'),
        max_length=20,
    )
    address = models.TextField(
        _('address'),
    )
    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        related_name='homeworkers',
        verbose_name=_('state'),
        null=True,
        blank=True,
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='homeworkers',
        verbose_name=_('city'),
        null=True,
        blank=True,
    )
    pincode = models.CharField(
        _('pincode'),
        max_length=10,
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('homeworker')
        verbose_name_plural = _('homeworkers')
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.name} ({self.client.company_name})'
