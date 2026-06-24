import random
from datetime import timedelta

from django.utils import timezone
from django.core.management.base import BaseCommand

from clients.models import Client
from hosting.models import DomainHosting, DomainHostingInvoice


SERVICES_DATA = [
    {
        'service_type': 'domain',
        'service_name': 'techsolutions.in',
        'provider': 'GoDaddy',
        'renewal_amount': 899,
        'gst_percent': 18,
        'nameserver': 'ns1.godaddy.com',
        'ip_address': '192.168.1.10',
        'notes': 'Primary business domain',
    },
    {
        'service_type': 'domain',
        'service_name': 'cloudserve.co',
        'provider': 'Namecheap',
        'renewal_amount': 1200,
        'gst_percent': 18,
        'nameserver': 'ns1.namecheap.com',
        'ip_address': None,
        'notes': 'Client portal domain',
    },
    {
        'service_type': 'hosting',
        'service_name': 'TechCloud Basic Plan',
        'provider': 'HostGator',
        'renewal_amount': 3500,
        'gst_percent': 18,
        'nameserver': 'ns1.hostgator.com',
        'ip_address': '103.21.58.120',
        'notes': '50GB SSD, 1TB bandwidth',
    },
    {
        'service_type': 'hosting',
        'service_name': 'AWS Lightsail',
        'provider': 'Amazon Web Services',
        'renewal_amount': 8400,
        'gst_percent': 18,
        'nameserver': 'ns1.amazonaws.com',
        'ip_address': '52.66.193.44',
        'notes': '2GB RAM, 60GB SSD, 3TB transfer',
    },
    {
        'service_type': 'domain',
        'service_name': 'freshmarts.com',
        'provider': 'Google Domains',
        'renewal_amount': 1050,
        'gst_percent': 18,
        'nameserver': 'ns1.google.com',
        'ip_address': None,
        'notes': 'E-commerce client domain',
    },
    {
        'service_type': 'hosting',
        'service_name': 'DigitalOcean Starter',
        'provider': 'DigitalOcean',
        'renewal_amount': 6000,
        'gst_percent': 18,
        'nameserver': 'ns1.digitalocean.com',
        'ip_address': '167.71.233.101',
        'notes': '4GB RAM, 80GB SSD, 5TB transfer',
    },
    {
        'service_type': 'domain',
        'service_name': 'smartlogistics.net',
        'provider': 'BigRock',
        'renewal_amount': 750,
        'gst_percent': 18,
        'nameserver': 'ns1.bigrock.com',
        'ip_address': None,
        'notes': 'Logistics client domain',
    },
    {
        'service_type': 'hosting',
        'service_name': 'VPS Pro Plan',
        'provider': 'Bluehost',
        'renewal_amount': 12000,
        'gst_percent': 18,
        'nameserver': 'ns1.bluehost.com',
        'ip_address': '162.241.217.98',
        'notes': '4 vCPU, 8GB RAM, 200GB SSD',
    },
    {
        'service_type': 'domain',
        'service_name': 'greenenergy.org',
        'provider': 'GoDaddy',
        'renewal_amount': 999,
        'gst_percent': 18,
        'nameserver': 'ns1.godaddy.com',
        'ip_address': None,
        'notes': 'NGO client domain',
    },
    {
        'service_type': 'hosting',
        'service_name': 'Azure Web App',
        'provider': 'Microsoft Azure',
        'renewal_amount': 15600,
        'gst_percent': 18,
        'nameserver': 'ns1.azure.com',
        'ip_address': '20.204.105.12',
        'notes': 'B1 plan, 1 vCPU, 1.75GB RAM',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with sample domain and hosting services'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing services before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            DomainHosting.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared all existing services.'))

        clients = list(Client.objects.filter(is_active=True))
        if not clients:
            self.stdout.write(self.style.ERROR('No active clients found. Create clients first.'))
            return

        today = timezone.now().date()
        created = 0

        for i, data in enumerate(SERVICES_DATA):
            client = clients[i % len(clients)]

            # Vary expiry dates: some expired, some expiring soon, some active
            if i < 2:
                expiry = today - timedelta(days=random.randint(1, 30))
                status = DomainHosting.Status.EXPIRED
            elif i < 4:
                expiry = today + timedelta(days=random.randint(1, 9))
                status = DomainHosting.Status.ACTIVE
            elif i < 6:
                expiry = today + timedelta(days=random.randint(11, 60))
                status = DomainHosting.Status.ACTIVE
            elif i < 8:
                expiry = today + timedelta(days=random.randint(100, 365))
                status = DomainHosting.Status.ACTIVE
            else:
                expiry = today + timedelta(days=random.randint(30, 180))
                status = DomainHosting.Status.ACTIVE

            reg_date = today - timedelta(days=random.randint(180, 730))

            service = DomainHosting.objects.create(
                client=client,
                registration_date=reg_date,
                expiry_date=expiry,
                status=status,
                is_active=True,
                reminder_sent=(status == DomainHosting.Status.EXPIRED),
                **data,
            )

            # Add 1-2 invoices per service
            for j in range(random.randint(1, 2)):
                inv_date = reg_date + timedelta(days=365 * j)
                DomainHostingInvoice.objects.create(
                    service=service,
                    invoice_number=f'INV-{service.pk:04d}-{j + 1:02d}',
                    invoice_date=inv_date,
                    amount=data['renewal_amount'] * (1 + data['gst_percent'] / 100),
                    paid=random.choice([True, True, False]),
                    paid_date=inv_date + timedelta(days=random.randint(1, 15)) if random.random() > 0.3 else None,
                    notes=f'Annual renewal {inv_date.year}',
                )

            created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created} services with invoices.'))
