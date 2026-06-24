from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """In-app notification for users."""

    class Level(models.TextChoices):
        INFO = 'info', _('Info')
        SUCCESS = 'success', _('Success')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('recipient'),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='acted_notifications',
        verbose_name=_('actor'),
        null=True,
        blank=True,
    )
    verb = models.CharField(
        _('verb'),
        max_length=255,
    )
    level = models.CharField(
        _('level'),
        max_length=10,
        choices=Level.choices,
        default=Level.INFO,
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(
        _('object ID'),
        null=True,
        blank=True,
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    is_read = models.BooleanField(_('read'), default=False)
    created_at = models.DateTimeField(_('created at'), default=timezone.now)

    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self) -> str:
        return f'{self.verb} → {self.recipient}'

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])

    @classmethod
    def create(cls, recipient, verb, level='info', actor=None, target=None):
        """Helper to create a notification."""
        kwargs = {
            'recipient': recipient,
            'verb': verb,
            'level': level,
            'actor': actor,
        }
        if target is not None:
            kwargs['content_type'] = ContentType.objects.get_for_model(target)
            kwargs['object_id'] = target.pk
        return cls.objects.create(**kwargs)
