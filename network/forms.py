from django import forms

from clients.models import Client

from .models import NetworkDevice


class NetworkDeviceForm(forms.ModelForm):
    """Form for creating and updating NetworkDevice records."""

    class Meta:
        model = NetworkDevice
        fields = [
            'name', 'device_type', 'ip_address', 'subnet', 'mac_address', 'brand',
            'model_name', 'serial_number', 'client', 'homeworker', 'location',
            'username', 'password', 'notes', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'device_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'ip_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': '192.168.1.10'}),
            'subnet': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': '192.168.1.0/24'}),
            'mac_address': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'AA:BB:CC:DD:EE:FF'}),
            'brand': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'model_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'serial_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'homeworker': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'location': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'username': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'password': forms.PasswordInput(attrs={'class': 'input input-bordered w-full', 'autocomplete': 'off'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from clients.models import Client, Homeworker
        self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['client'].required = False
        self.fields['homeworker'].queryset = Homeworker.objects.filter(is_active=True)
        self.fields['homeworker'].required = False
