from django import forms

from .models import AISettings


class AISettingsForm(forms.ModelForm):
    class Meta:
        model = AISettings
        fields = [
            'provider', 'api_key', 'model_name', 'base_url',
            'max_tokens', 'temperature', 'cache_ttl',
            'daily_budget', 'is_active',
        ]
        widgets = {
            'provider': forms.Select(attrs={'class': 'select select-bordered select-sm w-full'}),
            'api_key': forms.PasswordInput(
                attrs={'class': 'input input-bordered input-sm w-full', 'placeholder': 'sk-...'},
                render_value=True,
            ),
            'model_name': forms.TextInput(
                attrs={'class': 'input input-bordered input-sm w-full', 'placeholder': 'e.g. gpt-4o-mini'},
            ),
            'base_url': forms.URLInput(
                attrs={'class': 'input input-bordered input-sm w-full', 'placeholder': 'Leave blank for default'},
            ),
            'max_tokens': forms.NumberInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'temperature': forms.NumberInput(attrs={'class': 'input input-bordered input-sm w-full', 'step': '0.1', 'min': '0', 'max': '2'}),
            'cache_ttl': forms.NumberInput(attrs={'class': 'input input-bordered input-sm w-full'}),
            'daily_budget': forms.NumberInput(attrs={'class': 'input input-bordered input-sm w-full', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-sm'}),
        }
