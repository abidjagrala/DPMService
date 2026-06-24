import logging
import requests

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

MSG91_API_URL = 'https://api.msg91.com/api/v5/otp'


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


def send_sms_notification(phone_number, message):
    if not phone_number or not settings.MSG91_API_KEY:
        return
    try:
        headers = {
            'authkey': settings.MSG91_API_KEY,
            'Content-Type': 'application/json',
        }
        payload = {
            'sender': settings.MSG91_SENDER_ID,
            'route': '4',
            'country': '91',
            'sms': [
                {'message': message, 'to': [phone_number]},
            ],
        }
        response = requests.post(
            MSG91_API_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            logger.error('SMS send failed to %s: %s', phone_number, response.text)
    except Exception as e:
        logger.error('SMS send failed to %s: %s', phone_number, e)


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
    sms_msg = f'DPM Service: New ticket {ticket.ticket_number} created for {ticket.client.company_name}. Subject: {ticket.subject}'

    if ticket.client and ticket.client.email:
        send_email_notification(subject, message, ticket.client.email)
    if ticket.client and ticket.client.phone:
        send_sms_notification(ticket.client.phone, sms_msg)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)
        phone = _get_admin_phone(admin)
        if phone:
            send_sms_notification(phone, sms_msg)


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
    sms_msg = f'DPM Service: Ticket {ticket.ticket_number} assigned to you. Subject: {ticket.subject}'

    if ticket.assigned_to and ticket.assigned_to.user and ticket.assigned_to.user.email:
        send_email_notification(subject, message, ticket.assigned_to.user.email)
    if ticket.assigned_to and ticket.assigned_to.phone:
        send_sms_notification(ticket.assigned_to.phone, sms_msg)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)
        phone = _get_admin_phone(admin)
        if phone:
            send_sms_notification(phone, f'DPM Service: Ticket {ticket.ticket_number} assigned to {ticket.assigned_to.user.get_full_name()}.')


def notify_ticket_closed(ticket):
    subject = f'Ticket Closed: {ticket.ticket_number}'
    message = (
        f'Ticket {ticket.ticket_number} has been closed.\n\n'
        f'Subject: {ticket.subject}\n'
        f'Client: {ticket.client.company_name}\n'
        f'Completed Date: {ticket.completed_date}\n'
    )
    sms_msg = f'DPM Service: Ticket {ticket.ticket_number} has been closed. Subject: {ticket.subject}'

    if ticket.client and ticket.client.email:
        send_email_notification(subject, message, ticket.client.email)
    if ticket.client and ticket.client.phone:
        send_sms_notification(ticket.client.phone, sms_msg)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)
        phone = _get_admin_phone(admin)
        if phone:
            send_sms_notification(phone, sms_msg)


def notify_device_assigned(asset, client=None, homeworker=None):
    target_name = client.company_name if client else (homeworker.name if homeworker else 'Unknown')
    subject = f'Device Assigned: {asset.asset_tag}'
    message = (
        f'Device {asset.asset_tag} ({asset.brand} {asset.model_name}) '
        f'has been assigned.\n\n'
        f'Assigned To: {target_name}\n'
        f'Status: {asset.get_status_display()}\n'
    )
    sms_msg = f'DPM Service: Device {asset.asset_tag} assigned to {target_name}.'

    if client and client.email:
        send_email_notification(subject, message, client.email)
    if client and client.phone:
        send_sms_notification(client.phone, sms_msg)

    from accounts.models import User
    admins = User.objects.filter(role='admin', is_active=True)
    for admin in admins:
        if admin.email:
            send_email_notification(subject, message, admin.email)
        phone = _get_admin_phone(admin)
        if phone:
            send_sms_notification(phone, sms_msg)


def _get_admin_phone(user):
    from clients.models import Employee
    try:
        emp = Employee.objects.get(user=user)
        return emp.phone
    except Employee.DoesNotExist:
        return None
