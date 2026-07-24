from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db import models
from django.utils.translation import gettext_lazy as _

from .models import CompanyInfo, MailSettings, SmsSettings, WhatsappSettings

User = get_user_model()


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.lower() if email else email


class PasswordResetConfirmForm(forms.Form):
    new_password1 = forms.CharField(
        label=_('New password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label=_('Confirm new password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password2(self):
        p1 = self.cleaned_data.get('new_password1')
        p2 = self.cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        password_validation.validate_password(p2, self.user)
        return p2

    def save(self):
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.clear_password_reset_token()
        self.user.save()


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    error_messages = {
        'invalid_login': _('Please enter a correct email and password.'),
        'inactive': _('This account is inactive.'),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            if not self.user_cache.is_active:
                raise forms.ValidationError(
                    self.error_messages['inactive'],
                    code='inactive',
                )
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email.lower() if email else email


class AdminUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_('Password confirmation'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        password_validation.validate_password(p2, self.instance)
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class AdminUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label=_('Password'),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change the password using "
            "<a href=\"../password/\">this form</a>."
        ),
    )

    class Meta:
        model = User
        fields = (
            'email', 'password', 'first_name', 'last_name', 'role',
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',
        )

    def clean_password(self):
        return self.initial.get('password')


class AdminUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_('Password'),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='',
    )
    password2 = forms.CharField(
        label=_('Password confirmation'),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='',
    )
    client_profile = forms.ModelChoiceField(
        label=_('Client'),
        queryset=None,
        required=False,
        empty_label=_('Select client...'),
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.pop('is_create', False)
        super().__init__(*args, **kwargs)

        from clients.models import Client
        if self.instance.pk:
            linked_client = Client.objects.filter(user=self.instance).first()
            available_clients = Client.objects.filter(models.Q(user__isnull=True) | models.Q(user=self.instance)).order_by('company_name')
        else:
            linked_client = None
            available_clients = Client.objects.filter(user__isnull=True).order_by('company_name')

        self.fields['client_profile'].queryset = available_clients
        if linked_client:
            self.fields['client_profile'].initial = linked_client

        if self.is_create:
            self.fields['password1'].required = True
            self.fields['password2'].required = True
            self.fields['password1'].help_text = ''
            self.fields['password2'].help_text = ''
        else:
            self.fields['password1'].help_text = ''
            self.fields['password2'].help_text = ''

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email.lower() if email else email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        role = cleaned.get('role')

        if self.is_create or password1 or password2:
            if not password1:
                self.add_error('password1', _('This field is required.'))
            if not password2:
                self.add_error('password2', _('This field is required.'))
            if password1 and password2 and password1 != password2:
                self.add_error('password2', _("The two password fields didn't match."))
            if password2:
                try:
                    password_validation.validate_password(password2, self.instance)
                except forms.ValidationError as error:
                    self.add_error('password2', error)

        if role == User.Role.CLIENT:
            client_profile = cleaned.get('client_profile')
            if not client_profile:
                self.add_error('client_profile', _('Please select a client for client-role users.'))

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if self.is_create and not password:
            user.set_password(User.objects.make_random_password())
        if commit:
            user.save()
            self._save_client_link(user)
        return user

    def _save_client_link(self, user):
        from clients.models import Client
        role = self.cleaned_data.get('role')
        client_profile = self.cleaned_data.get('client_profile')

        old_linked = Client.objects.filter(user=user).first()
        if old_linked and old_linked != client_profile:
            old_linked.user = None
            old_linked.save(update_fields=['user'])

        if role == User.Role.CLIENT and client_profile:
            client_profile.user = user
            client_profile.save(update_fields=['user'])
        elif role != User.Role.CLIENT:
            pass


class CompanyInfoForm(forms.ModelForm):
    class Meta:
        model = CompanyInfo
        fields = [
            'name', 'tagline', 'address', 'city', 'state', 'pincode', 'country',
            'phone', 'email', 'website',
            'gst_number', 'pan_number', 'cin_number',
            'logo_light', 'logo_dark',
            'bank_name', 'bank_account_number', 'bank_ifsc', 'bank_branch',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'tagline': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'address': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'state': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'pincode': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'country': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'phone': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'email': forms.EmailInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'website': forms.URLInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'gst_number': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'pan_number': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'cin_number': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'bank_name': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'bank_ifsc': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'bank_branch': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
        }


class MailSettingsForm(forms.ModelForm):
    class Meta:
        model = MailSettings
        fields = [
            'host', 'port', 'security', 'username', 'password',
            'from_name', 'from_email', 'is_active',
        ]
        widgets = {
            'host': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'port': forms.NumberInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'security': forms.Select(attrs={'class': 'select select-bordered select-sm w-full'}),
            'username': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'password': forms.PasswordInput(attrs={'class': 'input input-bordered input-sm w-full'}, render_value=True),
            'from_name': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'from_email': forms.EmailInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-sm'}),
        }


class SmsSettingsForm(forms.ModelForm):
    class Meta:
        model = SmsSettings
        fields = ['auth_key', 'sender_id', 'route', 'country', 'is_active']
        widgets = {
            'auth_key': forms.PasswordInput(attrs={'class': 'input input-bordered input-sm w-full'}, render_value=True),
            'sender_id': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'route': forms.Select(attrs={'class': 'select select-bordered select-sm w-full'}),
            'country': forms.NumberInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-sm'}),
        }


class WhatsappSettingsForm(forms.ModelForm):
    class Meta:
        model = WhatsappSettings
        fields = ['auth_key', 'template_id', 'whatsapp_number', 'is_active']
        widgets = {
            'auth_key': forms.PasswordInput(attrs={'class': 'input input-bordered input-sm w-full'}, render_value=True),
            'template_id': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-sm'}),
        }
