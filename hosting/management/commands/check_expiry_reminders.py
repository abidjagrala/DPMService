import logging

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from django.core.management.base import BaseCommand

from hosting.models import DomainHosting
from notifications.models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Send expiry reminders for domain/hosting services expiring within 10 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=10,
            help='Number of days before expiry to send reminder (default: 10)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview which services would be notified without actually sending',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        today = timezone.now().date()
        cutoff = today + timedelta(days=days)

        services = DomainHosting.objects.select_related('client').filter(
            is_active=True,
            reminder_sent=False,
            expiry_date__lte=cutoff,
            expiry_date__gte=today,
        )

        count = 0
        for service in services:
            days_left = service.days_until_expiry
            self.stdout.write(
                f'  [{service.get_service_type_display()}] {service.service_name} '
                f'({service.client.company_name}) — expires {service.expiry_date} '
                f'({days_left} days left)'
            )

            if not dry_run:
                self._send_email(service, days_left)
                self._create_in_app_notification(service, days_left)
                service.reminder_sent = True
                service.save(update_fields=['reminder_sent'])
                count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry run — {services.count()} services found, none notified.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully sent {count} expiry reminder(s).'))

    def _send_email(self, service, days_left):
        subject = f'DPM Service: {service.get_service_type_display()} Expiring Soon — {service.service_name}'
        message = (
            f'This is a reminder that the following {service.get_service_type_display().lower()} '
            f'service is expiring in {days_left} day(s).\n\n'
            f'Service: {service.service_name}\n'
            f'Client: {service.client.company_name}\n'
            f'Provider: {service.provider or "N/A"}\n'
            f'Expiry Date: {service.expiry_date}\n'
            f'Days Remaining: {days_left}\n'
            f'Renewal Amount: ₹{service.renewal_amount}\n\n'
            f'Please take necessary action to renew before expiry.'
        )

        recipients = set()

        if service.client.email:
            recipients.add(service.client.email)

        admins = User.objects.filter(role='admin', is_active=True)
        for admin in admins:
            if admin.email:
                recipients.add(admin.email)

        for email in recipients:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error('Failed to send expiry reminder to %s: %s', email, e)

    def _create_in_app_notification(self, service, days_left):
        admins = User.objects.filter(role='admin', is_active=True)
        verb = (
            f'{service.get_service_type_display()} "{service.service_name}" '
            f'for {service.client.company_name} expires in {days_left} day(s) '
            f'on {service.expiry_date}.'
        )
        for admin in admins:
            Notification.create(
                recipient=admin,
                verb=verb,
                level=Notification.Level.WARNING,
                target=service,
            )
