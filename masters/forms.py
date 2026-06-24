from django import forms
from django.utils.translation import gettext_lazy as _

from .models import AssetType, City, ServiceType, State, TransportType


class StateForm(forms.ModelForm):
    """Form for creating and updating State records."""

    class Meta:
        model = State
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def clean_name(self) -> str:
        name = self.cleaned_data['name'].strip()
        qs = State.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A state with this name already exists.'))
        return name


class CityForm(forms.ModelForm):
    """Form for creating and updating City records."""

    class Meta:
        model = City
        fields = ['state', 'name', 'is_active']
        widgets = {
            'state': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def clean_name(self) -> str:
        name = self.cleaned_data['name'].strip()
        state = self.cleaned_data.get('state')
        if state:
            qs = City.objects.filter(state=state, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    _('A city with this name already exists in this state.')
                )
        return name


class ServiceTypeForm(forms.ModelForm):
    """Form for creating and updating ServiceType records."""

    class Meta:
        model = ServiceType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def clean_name(self) -> str:
        name = self.cleaned_data['name'].strip()
        qs = ServiceType.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A service type with this name already exists.'))
        return name


class AssetTypeForm(forms.ModelForm):
    """Form for creating and updating AssetType records."""

    class Meta:
        model = AssetType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def clean_name(self) -> str:
        name = self.cleaned_data['name'].strip()
        qs = AssetType.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('An asset type with this name already exists.'))
        return name


class TransportTypeForm(forms.ModelForm):
    """Form for creating and updating TransportType records."""

    class Meta:
        model = TransportType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def clean_name(self) -> str:
        name = self.cleaned_data['name'].strip()
        qs = TransportType.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A transport type with this name already exists.'))
        return name
