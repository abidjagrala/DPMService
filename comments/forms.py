from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    """Form for adding a generic comment."""

    class Meta:
        model = Comment
        fields = ['body', 'is_internal']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Write a comment…',
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-sm',
            }),
        }
