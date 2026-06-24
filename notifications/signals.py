from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from tickets.models import ServiceTicket

from .models import Notification
from .services import (
    notify_ticket_assigned,
    notify_ticket_closed,
    notify_ticket_created,
)


@receiver(pre_save, sender=ServiceTicket)
def _ticket_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = ServiceTicket.objects.get(pk=instance.pk)
            instance._old_status = old.status
            instance._old_assigned_to_id = old.assigned_to_id
        except ServiceTicket.DoesNotExist:
            instance._old_status = None
            instance._old_assigned_to_id = None
    else:
        instance._old_status = None
        instance._old_assigned_to_id = None


@receiver(post_save, sender=ServiceTicket)
def _ticket_post_save(sender, instance, created, **kwargs):
    actor = instance.created_by

    if created and actor:
        from accounts.models import User
        managers = User.objects.filter(role__in=['admin', 'manager'], is_active=True).exclude(pk=actor.pk)
        for manager in managers:
            Notification.create(
                recipient=manager,
                verb=f'New ticket {instance.ticket_number} created',
                level='info',
                actor=actor,
                target=instance,
            )
        notify_ticket_created(instance)

    old_status = getattr(instance, '_old_status', None)
    if old_status and old_status != instance.status and instance.created_by:
        Notification.create(
            recipient=instance.created_by,
            verb=f'Ticket {instance.ticket_number} status changed to {instance.get_status_display()}',
            level='success' if instance.status == 'completed' else 'info',
            actor=instance.assigned_to.user if instance.assigned_to else None,
            target=instance,
        )
        if instance.status == ServiceTicket.Status.COMPLETED:
            notify_ticket_closed(instance)

    old_assigned = getattr(instance, '_old_assigned_to_id', None)
    if old_assigned != instance.assigned_to_id and instance.assigned_to:
        Notification.create(
            recipient=instance.assigned_to.user,
            verb=f'You have been assigned ticket {instance.ticket_number}',
            level='info',
            actor=actor,
            target=instance,
        )
        notify_ticket_assigned(instance)
