from django import forms

from .models import (
    AuditLog, FieldPermission, Group, MenuPermission, MenuItem,
    ModelPermission, Module, ModulePermission, Role, UserRoleAssignment,
)


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'description', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ('name', 'description', 'group', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
            'group': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }


class UserRoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = UserRoleAssignment
        fields = ('user', 'role', 'group', 'is_active')
        widgets = {
            'user': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'role': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'group': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'checkbox checkbox-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields['user'].queryset = User.objects.filter(is_active=True).order_by('email')
        self.fields['role'].queryset = Role.objects.filter(is_active=True).order_by('name')
        self.fields['group'].queryset = Group.objects.filter(is_active=True).order_by('name')
        self.fields['group'].required = False


class ModulePermissionForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )
    module = forms.ModelChoiceField(
        queryset=Module.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )


class ModelPermissionBulkForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )


class FieldPermissionForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )
    model = forms.ChoiceField(
        choices=[('', '---')] + [(m[0], m[1]) for m in ModelPermission._meta.get_field('model').choices],
        widget=forms.Select(attrs={'class': 'select select-bordered w-full'}),
    )
