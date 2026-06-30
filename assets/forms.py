from django import forms
from django.utils.translation import gettext_lazy as _

from clients.models import Client, Homeworker
from masters.models import AssetType

from .models import Asset, AssetAssignment


class AssetForm(forms.ModelForm):
    """Form for creating and updating Asset records."""

    class Meta:
        model = Asset
        fields = [
            'asset_tag', 'serial_number', 'asset_type', 'brand_model',
            'purchase_date', 'warranty_expiry',
            'status', 'client', 'homeworker', 'ip_address', 'mac_address',
            'notes', 'username', 'password', 'is_active',
        ]
        widgets = {
            'asset_tag': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'serial_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'asset_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'brand_model': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'purchase_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'homeworker': forms.Select(attrs={'class': 'select select-bordered w-full'}),
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
        self.fields['homeworker'].queryset = Homeworker.objects.filter(is_active=True)
        self.fields['client'].required = False
        self.fields['homeworker'].required = False
        if self.instance.pk:
            self.fields['asset_tag'].disabled = True
        else:
            self.fields['asset_tag'].widget = forms.HiddenInput()

    def clean_asset_tag(self) -> str:
        asset_tag = self.cleaned_data.get('asset_tag', '').strip()
        if not asset_tag:
            return asset_tag
        qs = Asset.objects.filter(asset_tag__iexact=asset_tag)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('An asset with this tag already exists.'))
        return asset_tag

    def clean(self) -> dict:
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        homeworker = cleaned_data.get('homeworker')
        if status == Asset.Status.ASSIGNED and not homeworker:
            raise forms.ValidationError(_('Homeworker is required when status is Assigned.'))
        return cleaned_data


class AssetAssignForm(forms.Form):
    """Form for assigning an asset to a client or homeworker."""

    client = forms.ModelChoiceField(
        queryset=Client.objects.filter(is_active=True),
        required=False,
        label=_('Assign to Client'),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )
    homeworker = forms.ModelChoiceField(
        queryset=Homeworker.objects.filter(is_active=True),
        required=False,
        label=_('Assign to Homeworker'),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )
    notes = forms.CharField(
        required=False,
        label=_('Notes'),
        widget=forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
    )

    def clean(self) -> dict:
        cleaned_data = super().clean()
        client = cleaned_data.get('client')
        homeworker = cleaned_data.get('homeworker')
        if not client and not homeworker:
            raise forms.ValidationError(_('Please select either a client or a homeworker.'))
        if client and homeworker:
            raise forms.ValidationError(_('Please select only one: client or homeworker.'))
        return cleaned_data


class ClientAssetForm(forms.ModelForm):
    """Restricted form for client users to create/edit their own assets."""

    class Meta:
        model = Asset
        fields = [
            'serial_number', 'asset_type', 'brand_model',
            'purchase_date', 'warranty_expiry',
            'status', 'homeworker', 'ip_address', 'mac_address',
            'notes',
        ]
        widgets = {
            'serial_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'asset_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'brand_model': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'purchase_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'homeworker': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'ip_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': '192.168.1.10'}),
            'mac_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'AA:BB:CC:DD:EE:FF'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        if user and user.is_client:
            self.fields['homeworker'].queryset = Homeworker.objects.filter(is_active=True, client__user=user)
        else:
            self.fields['homeworker'].queryset = Homeworker.objects.filter(is_active=True)
        self.fields['homeworker'].required = False
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

    def clean(self) -> dict:
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        homeworker = cleaned_data.get('homeworker')
        if status == Asset.Status.ASSIGNED and not homeworker:
            raise forms.ValidationError(_('Homeworker is required when status is Assigned.'))
        return cleaned_data
