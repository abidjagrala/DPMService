import json as json_mod
import logging
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel helpers
# ---------------------------------------------------------------------------

def _apply_mail_settings():
    """Apply MailSettings from DB to Django settings. Returns True if email is active."""
    from accounts.models import MailSettings
    mail_config = MailSettings.get_instance()
    if not mail_config.is_active:
        return False
    mail_config.apply_to_settings()
    return True


def send_email_notification(subject, message, recipient_email):
    if not recipient_email:
        return
    if not _apply_mail_settings():
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


def send_sms_notification(message, phone):
    """Send SMS via MSG91. phone must include country code (e.g. 91XXXXXXXXXX)."""
    if not phone:
        return
    from accounts.models import SmsSettings
    sms_config = SmsSettings.get_instance()
    if not sms_config.is_active or not sms_config.auth_key:
        return
    try:
        payload = json_mod.dumps({
            'sender': sms_config.sender_id,
            'route': str(sms_config.route),
            'country': str(sms_config.country),
            'sms': [{'message': message, 'to': [phone]}],
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.msg91.com/api/v2/sendsms',
            data=payload,
            headers={
                'authkey': sms_config.auth_key,
                'Content-Type': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json_mod.loads(resp.read().decode('utf-8'))
        if result.get('type') != 'success':
            logger.error('SMS send failed to %s: %s', phone, result.get('message'))
    except Exception as e:
        logger.error('SMS send failed to %s: %s', phone, e)


def send_whatsapp_notification(phone, template_id=None, variables=None):
    """Send WhatsApp template message via MSG91. phone must include country code."""
    if not phone:
        return
    from accounts.models import WhatsappSettings
    wa_config = WhatsappSettings.get_instance()
    if not wa_config.is_active or not wa_config.auth_key:
        return
    tpl = template_id or wa_config.template_id
    if not tpl:
        return
    if not wa_config.whatsapp_number:
        return
    try:
        payload = json_mod.dumps({
            'sender': wa_config.whatsapp_number,
            'number': phone,
            'template_id': tpl,
            'variables': variables or [],
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.msg91.com/api/v5/whatsapp/send/template',
            data=payload,
            headers={
                'authkey': wa_config.auth_key,
                'Content-Type': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json_mod.loads(resp.read().decode('utf-8'))
        if result.get('type') != 'success':
            logger.error('WhatsApp send failed to %s: %s', phone, result.get('message'))
    except Exception as e:
        logger.error('WhatsApp send failed to %s: %s', phone, e)


# ---------------------------------------------------------------------------
# Convenience: dispatch to all active channels
# ---------------------------------------------------------------------------

def _notify_all_channels(subject, message, email=None, phone=None, whatsapp_vars=None):
    """Send a notification through email, SMS, and WhatsApp where available."""
    if email:
        send_email_notification(subject, message, email)
    if phone:
        send_sms_notification(message, phone)
    if phone:
        send_whatsapp_notification(phone, variables=whatsapp_vars or [])


def _get_admin_emails():
    from accounts.models import User
    return list(
        User.objects.filter(role='admin', is_active=True)
        .values_list('email', flat=True)
    )


# ---------------------------------------------------------------------------
# Ticket notifications
# ---------------------------------------------------------------------------

def notify_ticket_created(ticket):
    subject = f'New Ticket Created: {ticket.ticket_number}'
    message = (
        f'A new service ticket has been created.\n\n'
        f'Ticket: {ticket.ticket_number}\n'
        f'Subject: {ticket.subject}\n'
        f'Client: {ticket.client.company_name}\n'
        f'Client Phone: {ticket.client.phone}\n'
        f'Priority: {ticket.get_priority_display()}\n\n'
        f'Please review and take action.'
    )
    client_phone = ticket.client.phone if ticket.client else None
    client_email = ticket.client.email if ticket.client else None
    _notify_all_channels(
        subject, message,
        email=client_email,
        phone=client_phone,
        whatsapp_vars=[ticket.ticket_number, ticket.client.company_name],
    )
    for admin_email in _get_admin_emails():
        send_email_notification(subject, message, admin_email)


def notify_ticket_assigned(ticket):
    subject = f'Ticket Assigned: {ticket.ticket_number}'
    assignee_phone = ticket.assigned_to.phone if ticket.assigned_to else None
    message = (
        f'Ticket {ticket.ticket_number} has been assigned.\n\n'
        f'Subject: {ticket.subject}\n'
        f'Client: {ticket.client.company_name}\n'
        f'Client Phone: {ticket.client.phone}\n'
        f'Assigned To: {ticket.assigned_to.user.get_full_name() if ticket.assigned_to else "N/A"}\n'
        f'Assignee Phone: {assignee_phone or "N/A"}\n'
        f'Priority: {ticket.get_priority_display()}\n'
        f'Scheduled Date: {ticket.scheduled_date or "Not set"}\n'
    )
    if ticket.assigned_to and ticket.assigned_to.user:
        _notify_all_channels(
            subject, message,
            email=ticket.assigned_to.user.email,
            phone=assignee_phone,
            whatsapp_vars=[ticket.ticket_number, ticket.subject],
        )
    for admin_email in _get_admin_emails():
        send_email_notification(subject, message, admin_email)


def notify_ticket_closed(ticket):
    subject = f'Ticket Closed: {ticket.ticket_number}'
    message = (
        f'Ticket {ticket.ticket_number} has been closed.\n\n'
        f'Subject: {ticket.subject}\n'
        f'Client: {ticket.client.company_name}\n'
        f'Client Phone: {ticket.client.phone}\n'
        f'Completed Date: {ticket.completed_date}\n'
    )
    client_phone = ticket.client.phone if ticket.client else None
    client_email = ticket.client.email if ticket.client else None
    _notify_all_channels(
        subject, message,
        email=client_email,
        phone=client_phone,
        whatsapp_vars=[ticket.ticket_number, ticket.subject],
    )
    for admin_email in _get_admin_emails():
        send_email_notification(subject, message, admin_email)


# ---------------------------------------------------------------------------
# Device / asset notifications
# ---------------------------------------------------------------------------

def notify_device_assigned(asset, client=None):
    target_name = client.company_name if client else 'Unknown'
    subject = f'Device Assigned: {asset.serial_number or asset.pk}'
    message = (
        f'Device {asset.serial_number or asset.pk} ({asset.brand} {asset.model_name}) '
        f'has been assigned.\n\n'
        f'Assigned To: {target_name}\n'
        f'Client Phone: {client.phone if client else "N/A"}\n'
        f'Status: {asset.get_status_display()}\n'
    )
    client_phone = client.phone if client else None
    client_email = client.email if client else None
    _notify_all_channels(
        subject, message,
        email=client_email,
        phone=client_phone,
        whatsapp_vars=[asset.serial_number or str(asset.pk), target_name],
    )
    for admin_email in _get_admin_emails():
        send_email_notification(subject, message, admin_email)
