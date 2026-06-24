from django import forms
from django.utils.translation import gettext_lazy as _

from assets.models import Asset
from clients.models import Client, Employee
from masters.models import ServiceType, TransportType

from .models import ServiceTicket, TicketComment


class ServiceTicketForm(forms.ModelForm):
    """Form for creating and updating ServiceTicket records."""

    class Meta:
        model = ServiceTicket
        fields = [
            'service_type', 'client', 'asset', 'assigned_to',
            'priority', 'subject', 'description', 'scheduled_date',
            'address', 'contact_person', 'contact_phone',
            'transport_type', 'tracking_url',
            'notes', 'status',
        ]
        widgets = {
            'service_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'asset': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'assigned_to': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'priority': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'subject': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'scheduled_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
            'contact_person': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'contact_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'transport_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'tracking_url': forms.URLInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'https://...'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['asset'].queryset = Asset.objects.filter(is_active=True)
        self.fields['assigned_to'].queryset = Employee.objects.filter(is_active=True)
        self.fields['transport_type'].queryset = TransportType.objects.filter(is_active=True)
        self.fields['asset'].required = False
        self.fields['assigned_to'].required = False
        self.fields['scheduled_date'].required = False
        self.fields['address'].required = False
        self.fields['transport_type'].required = False
        self.fields['tracking_url'].required = False
        self.fields['notes'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        transport_type = self.cleaned_data.get('transport_type')
        if transport_type and 'self' in transport_type.name.lower():
            instance.tracking_url = ''
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        service_type = cleaned_data.get('service_type')
        transport_type = cleaned_data.get('transport_type')
        tracking_url = cleaned_data.get('tracking_url')

        pickup_drop_names = {'pickup', 'drop'}
        if service_type and service_type.name.lower() in pickup_drop_names:
            if not transport_type:
                self.add_error('transport_type', _('Transport type is required for pickup/drop services.'))

        return cleaned_data


class TicketCommentForm(forms.ModelForm):
    """Form for adding a comment to a ticket."""

    class Meta:
        model = TicketComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Add a comment...',
            }),
        }


class TicketStatusForm(forms.Form):
    """Quick form to update ticket status."""

    status = forms.ChoiceField(
        choices=ServiceTicket.Status.choices,
        widget=forms.Select(attrs={'class': 'select select-bordered select-sm w-full'}),
    )


class ClientTicketForm(forms.ModelForm):
    """Restricted form for client users to create/edit tickets."""

    class Meta:
        model = ServiceTicket
        fields = [
            'service_type', 'priority', 'subject', 'description',
            'address', 'contact_person', 'contact_phone',
        ]
        widgets = {
            'service_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'priority': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'subject': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'address': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
            'contact_person': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'contact_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_type'].queryset = ServiceType.objects.filter(is_active=True)
        self.fields['address'].required = False
        self.fields['contact_person'].required = False
        self.fields['contact_phone'].required = False


class StaffTicketForm(forms.ModelForm):
    """Restricted form for staff users to create tickets."""

    class Meta:
        model = ServiceTicket
        fields = [
            'service_type', 'client', 'priority', 'subject', 'description',
            'address', 'contact_person', 'contact_phone',
        ]
        widgets = {
            'service_type': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'client': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'priority': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'subject': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'address': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2}),
            'contact_person': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'contact_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service_type'].queryset = ServiceType.objects.filter(is_active=True)
        self.fields['client'].queryset = Client.objects.filter(is_active=True)
        self.fields['address'].required = False
        self.fields['contact_person'].required = False
        self.fields['contact_phone'].required = False
