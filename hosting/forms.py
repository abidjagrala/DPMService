from django import forms
from django.utils.translation import gettext_lazy as _

from clients.models import Client

from .models import DomainHosting, DomainHostingInvoice, AnnualMaintenanceContract


class DomainHostingForm(forms.ModelForm):
    """Form for creating and updating DomainHosting records."""

    class Meta:
        model = DomainHosting
        fields = [
            'client', 'service_type', 'service_name', 'provider',
            'registration_date', 'expiry_date', 'renewal_amount', 'gst_percent',
            'status', 'nameserver', 'ip_address', 'notes', 'is_active',
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'service_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'service_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'provider': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'registration_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'renewal_amount': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01'}),
            'gst_percent': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'nameserver': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'ip_address': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(is_active=True)

    def clean_service_name(self) -> str:
        return self.cleaned_data['service_name'].strip().lower()


class DomainHostingInvoiceForm(forms.ModelForm):
    """Form for creating and updating invoice records."""

    class Meta:
        model = DomainHostingInvoice
        fields = [
            'invoice_number', 'invoice_date', 'amount', 'paid', 'paid_date', 'notes',
        ]
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'invoice_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01'}),
            'paid': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
            'paid_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
        }


class AMCForm(forms.ModelForm):
    """Form for creating and updating AnnualMaintenanceContract records."""

    class Meta:
        model = AnnualMaintenanceContract
        fields = ['title', 'client', 'description', 'expiry_date', 'amount', 'payment_status', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'expiry_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['description'].required = False
