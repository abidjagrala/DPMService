from django import forms
from django.utils.translation import gettext_lazy as _

from masters.models import City, State

from .models import Client, Employee, Homeworker

EMPLOYEE_PHOTO_MAX = 1 * 1024 * 1024  # 1 MB
AADHAR_CARD_MAX = 1 * 1024 * 1024  # 1 MB
EMPLOYEE_PHOTO_TYPES = ['image/png', 'image/jpeg']
AADHAR_CARD_TYPES = ['image/png', 'image/jpeg', 'application/pdf']


class ClientForm(forms.ModelForm):
    """Form for creating and updating Client records."""

    class Meta:
        model = Client
        fields = [
            'company_name', 'contact_person', 'email', 'phone', 'alt_phone',
            'address', 'state', 'city', 'pincode', 'gst_number', 'pan_number',
            'is_active',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'contact_person': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
            'phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'alt_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'address': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'state': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'city': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'pincode': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'gst_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'pan_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def clean_email(self) -> str:
        email = self.cleaned_data['email'].strip().lower()
        qs = Client.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A client with this email already exists.'))
        return email

    def clean_phone(self) -> str:
        phone = self.cleaned_data['phone'].strip()
        # Basic phone validation - digits, spaces, hyphens, plus
        import re
        if not re.match(r'^[\d\s\-\+]+$', phone):
            raise forms.ValidationError(_('Enter a valid phone number.'))
        return phone


class EmployeeForm(forms.ModelForm):
    """Form for creating and updating Employee records."""

    first_name = forms.CharField(
        label=_('First name'),
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
    )
    last_name = forms.CharField(
        label=_('Last name'),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
    )
    email = forms.EmailField(
        label=_('Email address'),
        widget=forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
    )
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'input input-bordered w-full'}),
        required=False,
    )
    password2 = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput(attrs={'class': 'input input-bordered w-full'}),
        required=False,
    )

    class Meta:
        model = Employee
        fields = [
            'employee_id', 'designation', 'department', 'phone', 'alt_phone',
            'address', 'state', 'city', 'pincode', 'joining_date', 'is_active',
            'employee_photo', 'aadhar_card',
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'designation': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'department': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'alt_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'address': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'state': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'city': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'pincode': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'joining_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
            'employee_photo': forms.ClearableFileInput(attrs={'class': 'file-input file-input-bordered file-input-sm w-full', 'accept': 'image/png,image/jpeg'}),
            'aadhar_card': forms.ClearableFileInput(attrs={'class': 'file-input file-input-bordered file-input-sm w-full', 'accept': 'image/png,image/jpeg,application/pdf'}),
        }

    def __init__(self, *args, is_create: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_create = is_create
        if not is_create:
            self.fields['password1'].widget = forms.HiddenInput()
            self.fields['password2'].widget = forms.HiddenInput()
            self.fields['password1'].required = False
            self.fields['password2'].required = False

    def clean_email(self) -> str:
        email = self.cleaned_data['email'].strip().lower()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email

    def clean_employee_id(self) -> str:
        employee_id = self.cleaned_data['employee_id'].strip()
        qs = Employee.objects.filter(employee_id__iexact=employee_id)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('An employee with this ID already exists.'))
        return employee_id

    def clean_employee_photo(self):
        photo = self.cleaned_data.get('employee_photo')
        if photo:
            if photo.size > EMPLOYEE_PHOTO_MAX:
                raise forms.ValidationError(_('File size must be under 1 MB.'))
            if photo.content_type not in EMPLOYEE_PHOTO_TYPES:
                raise forms.ValidationError(_('Only PNG and JPG files are allowed.'))
        return photo

    def clean_aadhar_card(self):
        aadhar = self.cleaned_data.get('aadhar_card')
        if aadhar:
            if aadhar.size > AADHAR_CARD_MAX:
                raise forms.ValidationError(_('File size must be under 1 MB.'))
            if aadhar.content_type not in AADHAR_CARD_TYPES:
                raise forms.ValidationError(_('Only PNG, JPG, and PDF files are allowed.'))
        return aadhar

    def clean(self) -> dict:
        cleaned_data = super().clean()
        if self.is_create:
            password1 = cleaned_data.get('password1')
            password2 = cleaned_data.get('password2')
            if password1 and password2 and password1 != password2:
                self.add_error('password2', _('Passwords do not match.'))
            elif not password1:
                self.add_error('password1', _('Password is required for new employees.'))
        return cleaned_data


class HomeworkerForm(forms.ModelForm):
    """Form for creating and updating Homeworker records."""

    class Meta:
        model = Homeworker
        fields = [
            'client', 'name', 'email', 'phone', 'address',
            'state', 'city', 'pincode', 'is_active',
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'email': forms.EmailInput(attrs={'class': 'input input-bordered w-full'}),
            'phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'address': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'state': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'city': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'pincode': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        if user and user.is_client:
            self.fields['client'].widget = forms.HiddenInput()
            self.fields['client'].required = False
            self.fields['client'].queryset = Client.objects.filter(user=user)
        else:
            self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['state'].queryset = self.fields['state'].queryset.filter(is_active=True)
        self.fields['city'].queryset = self.fields['city'].queryset.filter(is_active=True)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._user and self._user.is_client:
            instance.client = self._user.client_profile
        if commit:
            instance.save()
        return instance
