from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import CompanyInfo, MailSettings, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm

    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Role & permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Two-Factor Authentication'), {
            'fields': ('totp_secret', 'two_factor_enabled'),
            'description': _('To disable 2FA for a user, clear the TOTP secret and uncheck "two-factor enabled".'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'gst_number', 'pan_number', 'phone', 'email')

    def has_add_permission(self, request):
        return not CompanyInfo.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MailSettings)
class MailSettingsAdmin(admin.ModelAdmin):
    list_display = ('host', 'port', 'security', 'username', 'is_active')

    def has_add_permission(self, request):
        return not MailSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
