from django import forms

from .models import Comment

COMMENT_ATTACHMENT_MAX = 1 * 1024 * 1024  # 1 MB
COMMENT_ATTACHMENT_TYPES = ['image/png', 'image/jpeg']


class CommentForm(forms.ModelForm):
    """Form for adding a generic comment."""

    class Meta:
        model = Comment
        fields = ['body', 'is_internal', 'attachment']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Write a comment...',
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-sm',
            }),
            'attachment': forms.ClearableFileInput(attrs={
                'class': 'file-input file-input-bordered file-input-sm w-full',
                'accept': 'image/png,image/jpeg',
            }),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            if attachment.size > COMMENT_ATTACHMENT_MAX:
                raise forms.ValidationError('File size must be under 1 MB.')
            if attachment.content_type not in COMMENT_ATTACHMENT_TYPES:
                raise forms.ValidationError('Only PNG and JPG files are allowed.')
        return attachment
