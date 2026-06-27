import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_email_notification(subject, message, recipient_email):
    if not recipient_email or not settings.EMAIL_HOST_USER:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error('Email send failed to %s: %s', recipient_email, e)


def notify_ticket_created(ticket):
    subject = f'New Ticket Created: {ticket.ticket_number}'
    message = (
        f'A new service ticket has been created.\n\n'
        f'Ticket: {ticket.ticket_number}\n'
        f'Subject: {ticket.subject}\n'
        f'Client: {ticket.client.company_name}\n'
        f'Priority: {ticket.get_priority_display()}\n\n'
        f'Please review and take action.'
    )
    if ticket.client and ticket.client.email:
        send_email_notification(subject, message, ticket.client.email)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)


def notify_ticket_assigned(ticket):
    subject = f'Ticket Assigned: {ticket.ticket_number}'
    message = (
        f'Ticket {ticket.ticket_number} has been assigned.\n\n'
        f'Subject: {ticket.subject}\n'
        f'Client: {ticket.client.company_name}\n'
        f'Assigned To: {ticket.assigned_to.user.get_full_name()}\n'
        f'Priority: {ticket.get_priority_display()}\n'
        f'Scheduled Date: {ticket.scheduled_date or "Not set"}\n'
    )
    if ticket.assigned_to and ticket.assigned_to.user and ticket.assigned_to.user.email:
        send_email_notification(subject, message, ticket.assigned_to.user.email)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)


def notify_ticket_closed(ticket):
    subject = f'Ticket Closed: {ticket.ticket_number}'
    message = (
        f'Ticket {ticket.ticket_number} has been closed.\n\n'
        f'Subject: {ticket.subject}\n'
        f'Client: {ticket.client.company_name}\n'
        f'Completed Date: {ticket.completed_date}\n'
    )
    if ticket.client and ticket.client.email:
        send_email_notification(subject, message, ticket.client.email)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)


def notify_device_assigned(asset, client=None, homeworker=None):
    target_name = client.company_name if client else (homeworker.name if homeworker else 'Unknown')
    subject = f'Device Assigned: {asset.asset_tag}'
    message = (
        f'Device {asset.asset_tag} ({asset.brand} {asset.model_name}) '
        f'has been assigned.\n\n'
        f'Assigned To: {target_name}\n'
        f'Status: {asset.get_status_display()}\n'
    )
    if client and client.email:
        send_email_notification(subject, message, client.email)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)

