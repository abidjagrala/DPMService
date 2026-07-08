import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('An email address is required.'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', User.Role.CLIENT)
        return self._create_user(email, password, **extra_fields)

    def create_manager(self, email, password=None, **extra_fields):
        extra_fields['role'] = User.Role.MANAGER
        extra_fields.setdefault('is_staff', True)
        return self._create_user(email, password, **extra_fields)

    def create_staff(self, email, password=None, **extra_fields):
        extra_fields['role'] = User.Role.STAFF
        extra_fields.setdefault('is_staff', True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        MANAGER = 'manager', _('Manager')
        STAFF = 'staff', _('Staff')
        CLIENT = 'client', _('Client')

    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
    )

    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into the admin site.'),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    password_reset_token = models.UUIDField(_('password reset token'), null=True, blank=True, unique=True)
    password_reset_token_created_at = models.DateTimeField(_('password reset token created at'), null=True, blank=True)
    totp_secret = models.CharField(_('TOTP secret key'), max_length=32, blank=True, default='',
                                   help_text=_('Secret key for TOTP two-factor authentication'))
    two_factor_enabled = models.BooleanField(_('two-factor enabled'), default=False,
                                            help_text=_('Whether two-factor authentication is enabled'))

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.email

    def get_short_name(self):
        return self.first_name or self.email

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT

    def generate_password_reset_token(self):
        self.password_reset_token = uuid.uuid4()
        self.password_reset_token_created_at = timezone.now()
        self.save(update_fields=['password_reset_token', 'password_reset_token_created_at'])
        return self.password_reset_token

    def is_password_reset_token_valid(self):
        if not self.password_reset_token or not self.password_reset_token_created_at:
            return False
        age = timezone.now() - self.password_reset_token_created_at
        return age.total_seconds() < 3600

    def clear_password_reset_token(self):
        self.password_reset_token = None
        self.password_reset_token_created_at = None
        self.save(update_fields=['password_reset_token', 'password_reset_token_created_at'])


def company_logo_path(instance, filename):
    return f'company/logos/{filename}'


class CompanyInfo(models.Model):
    """Singleton model for company details displayed on invoices, PDFs, and app header."""

    name = models.CharField(_('company name'), max_length=255)
    tagline = models.CharField(_('tagline'), max_length=255, blank=True, default='')
    address = models.TextField(_('address'))
    city = models.CharField(_('city'), max_length=100, blank=True, default='')
    state = models.CharField(_('state'), max_length=100, blank=True, default='')
    pincode = models.CharField(_('pincode'), max_length=10, blank=True, default='')
    country = models.CharField(_('country'), max_length=100, default='India')
    phone = models.CharField(_('phone'), max_length=20, blank=True, default='')
    email = models.EmailField(_('email'), blank=True, default='')
    website = models.URLField(_('website'), blank=True, default='')
    gst_number = models.CharField(_('GST number'), max_length=20, blank=True, default='')
    pan_number = models.CharField(_('PAN number'), max_length=20, blank=True, default='')
    cin_number = models.CharField(_('CIN number'), max_length=30, blank=True, default='',
                                  help_text=_('Company Identification Number'))
    logo_light = models.ImageField(_('logo (light theme)'), upload_to=company_logo_path,
                                   blank=True, null=True,
                                   help_text=_('Logo displayed on light backgrounds'))
    logo_dark = models.ImageField(_('logo (dark theme)'), upload_to=company_logo_path,
                                  blank=True, null=True,
                                  help_text=_('Logo displayed on dark backgrounds'))
    bank_name = models.CharField(_('bank name'), max_length=200, blank=True, default='')
    bank_account_number = models.CharField(_('bank account number'), max_length=30, blank=True, default='')
    bank_ifsc = models.CharField(_('bank IFSC code'), max_length=20, blank=True, default='')
    bank_branch = models.CharField(_('bank branch'), max_length=200, blank=True, default='')
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('company info')
        verbose_name_plural = _('company info')

    def __str__(self):
        return self.name

    def clean(self):
        if not self.pk and CompanyInfo.objects.exists():
            raise ValidationError(_('Only one company info record is allowed.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Return the singleton instance, creating one if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'name': 'Your Company Name',
                'address': 'Your Company Address',
            }
        )
        return obj


class MailSettings(models.Model):
    """Singleton model for email/SMTP configuration."""

    class Security(models.TextChoices):
        TLS = 'tls', _('TLS (STARTTLS)')
        SSL = 'ssl', _('SSL/TLS')
        NONE = 'none', _('None')

    host = models.CharField(_('SMTP host'), max_length=200, default='smtp.gmail.com')
    port = models.PositiveIntegerField(_('SMTP port'), default=587)
    security = models.CharField(_('encryption'), max_length=4, choices=Security.choices, default=Security.TLS)
    username = models.CharField(_('username'), max_length=200, blank=True, default='')
    password = models.CharField(_('password'), max_length=200, blank=True, default='')
    from_email = models.EmailField(_('default from email'), blank=True, default='',
                                   help_text=_('Used as the sender address for all outgoing emails'))
    from_name = models.CharField(_('from name'), max_length=200, blank=True, default='',
                                 help_text=_('Display name shown in the from field'))
    is_active = models.BooleanField(_('enable email sending'), default=False)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('mail settings')
        verbose_name_plural = _('mail settings')

    def __str__(self):
        return f'{self.host}:{self.port} ({self.get_security_display()})'

    def clean(self):
        if not self.pk and MailSettings.objects.exists():
            raise ValidationError(_('Only one mail settings record is allowed.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Return the singleton instance, creating one if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'host': 'smtp.gmail.com',
            'port': 587,
            'security': cls.Security.TLS,
        })
        return obj

    def apply_to_settings(self):
        """Apply mail settings to Django's email configuration at runtime."""
        from django.conf import settings as django_settings
        django_settings.EMAIL_HOST = self.host
        django_settings.EMAIL_PORT = self.port
        django_settings.EMAIL_USE_TLS = self.security == self.Security.TLS
        django_settings.EMAIL_USE_SSL = self.security == self.Security.SSL
        django_settings.EMAIL_HOST_USER = self.username
        django_settings.EMAIL_HOST_PASSWORD = self.password
        if self.from_email:
            django_settings.DEFAULT_FROM_EMAIL = f'{self.from_name} <{self.from_email}>' if self.from_name else self.from_email
