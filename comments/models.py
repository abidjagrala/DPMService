from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class Comment(models.Model):
    """Generic comment attachable to any model via contenttypes."""

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('content type'),
    )
    object_id = models.PositiveIntegerField(_('object ID'))
    content_object = GenericForeignKey('content_type', 'object_id')

    body = models.TextField(_('comment'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='generic_comments',
        verbose_name=_('created by'),
        null=True,
    )
    is_internal = models.BooleanField(
        _('internal note'),
        default=False,
        help_text=_('Internal comments are only visible to staff.'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self) -> str:
        return f'Comment by {self.created_by} on {self.content_type}#{self.object_id}'
