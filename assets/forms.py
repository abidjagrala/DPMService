from django import forms
from django.utils.translation import gettext_lazy as _

from clients.models import Client
from masters.models import AssetType

from .models import Asset, AssetAssignment


class AssetForm(forms.ModelForm):
    """Form for creating and updating Asset records."""

    class Meta:
        model = Asset
        fields = [
            'serial_number', 'asset_type', 'brand_model',
            'purchase_date', 'warranty_expiry',
            'status', 'client', 'device_location',
            'ip_address', 'mac_address',
            'notes', 'username', 'password', 'is_active',
        ]
        widgets = {
            'serial_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'asset_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'brand_model': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'purchase_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'device_location': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'e.g. Building A, Floor 3, Desk 12'}),
            'ip_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': '192.168.1.10'}),
            'mac_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'AA:BB:CC:DD:EE:FF'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
            'username': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'password': forms.PasswordInput(attrs={'class': 'input input-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['client'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk and not self.cleaned_data.get('password'):
            pass
        elif instance.pk and not self.cleaned_data.get('password'):
            instance.password = Asset.objects.filter(pk=instance.pk).values_list('password', flat=True).first() or ''
        if commit:
            instance.save()
        return instance


class AssetAssignForm(forms.Form):
    """Form for assigning an asset to a client."""

    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(is_active=True),
        required=True,
        label=_('Assign to Client'),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )
    notes = forms.CharField(
        required=False,
        label=_('Notes'),
        widget=forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
    )

    def clean(self) -> dict:
        cleaned_data = super().clean()
        return cleaned_data


class ClientAssetForm(forms.ModelForm):
    """Restricted form for client users to create/edit their own assets."""

    class Meta:
        model = Asset
        fields = [
            'serial_number', 'asset_type', 'brand_model',
            'purchase_date', 'warranty_expiry',
            'status', 'device_location', 'ip_address', 'mac_address',
            'notes',
        ]
        widgets = {
            'serial_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'asset_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'brand_model': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'purchase_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'device_location': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'e.g. Building A, Floor 3, Desk 12'}),
            'ip_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': '192.168.1.10'}),
            'mac_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'AA:BB:CC:DD:EE:FF'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.fields['device_location'].required = False
        self.fields['warranty_expiry'].required = False
        self.fields['ip_address'].required = False
        self.fields['mac_address'].required = False
        self.fields['notes'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._user and self._user.is_client:
            instance.client = self._user.client_profile
        if commit:
            instance.save()
        return instance
