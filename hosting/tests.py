from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from clients.models import Client
from masters.models import City, State

from .forms import DomainHostingForm, DomainHostingInvoiceForm
from .models import DomainHosting, DomainHostingInvoice


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class DomainHostingModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.client = Client.objects.create(
            company_name='Acme Corp', contact_person='Mr. X',
            email='acme@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        self.service = DomainHosting.objects.create(
            client=self.client,
            service_type='domain',
            service_name='example.com',
            provider='GoDaddy',
            registration_date=date(2024, 1, 1),
            expiry_date=date(2025, 12, 31),
            renewal_amount=Decimal('1500.00'),
            gst_percent=Decimal('18.00'),
        )

    def test_str_domain(self):
        self.assertEqual(str(self.service), 'Domain: example.com')

    def test_str_hosting(self):
        self.service.service_type = 'hosting'
        self.service.save()
        self.assertEqual(str(self.service), 'Hosting: example.com')

    def test_defaults(self):
        self.assertEqual(self.service.status, 'active')
        self.assertTrue(self.service.is_active)
        self.assertFalse(self.service.reminder_sent)
        self.assertEqual(self.service.gst_percent, Decimal('18.00'))
        self.assertEqual(self.service.renewal_amount, Decimal('1500.00'))

    def test_ordering(self):
        DomainHosting.objects.create(
            client=self.client, service_type='hosting',
            service_name='host-a.com',
            registration_date=date(2024, 1, 1),
            expiry_date=date(2024, 6, 15),
        )
        DomainHosting.objects.create(
            client=self.client, service_type='domain',
            service_name='later.com',
            registration_date=date(2024, 1, 1),
            expiry_date=date(2026, 6, 15),
        )
        names = list(DomainHosting.objects.values_list('service_name', flat=True))
        self.assertEqual(names, ['later.com', 'example.com', 'host-a.com'])

    def test_days_until_expiry_future(self):
        self.service.expiry_date = timezone.now().date() + timedelta(days=30)
        self.service.save()
        self.assertEqual(self.service.days_until_expiry, 30)

    def test_days_until_expiry_past(self):
        self.service.expiry_date = timezone.now().date() - timedelta(days=5)
        self.service.save()
        self.assertEqual(self.service.days_until_expiry, -5)

    def test_days_until_expiry_today(self):
        self.service.expiry_date = timezone.now().date()
        self.service.save()
        self.assertEqual(self.service.days_until_expiry, 0)

    def test_is_expiring_soon_true(self):
        self.service.expiry_date = timezone.now().date() + timedelta(days=5)
        self.service.save()
        self.assertTrue(self.service.is_expiring_soon)

    def test_is_expiring_soon_false_boundary_zero(self):
        self.service.expiry_date = timezone.now().date()
        self.service.save()
        self.assertFalse(self.service.is_expiring_soon)

    def test_is_expiring_soon_false_boundary_eleven(self):
        self.service.expiry_date = timezone.now().date() + timedelta(days=11)
        self.service.save()
        self.assertFalse(self.service.is_expiring_soon)

    def test_is_expiring_soon_false_negative(self):
        self.service.expiry_date = timezone.now().date() - timedelta(days=1)
        self.service.save()
        self.assertFalse(self.service.is_expiring_soon)

    def test_is_expired_true(self):
        self.service.expiry_date = timezone.now().date() - timedelta(days=1)
        self.service.save()
        self.assertTrue(self.service.is_expired)

    def test_is_expired_false_today(self):
        self.service.expiry_date = timezone.now().date()
        self.service.save()
        self.assertFalse(self.service.is_expired)

    def test_is_expired_false_future(self):
        self.service.expiry_date = timezone.now().date() + timedelta(days=1)
        self.service.save()
        self.assertFalse(self.service.is_expired)

    def test_renewal_with_gst(self):
        result = self.service.renewal_with_gst
        expected = Decimal('1500.00') + (Decimal('1500.00') * Decimal('18.00') / 100)
        self.assertEqual(result, expected)

    def test_renewal_with_gst_zero(self):
        self.service.renewal_amount = Decimal('0')
        self.service.save()
        self.assertEqual(self.service.renewal_with_gst, Decimal('0'))

    def test_client_relationship(self):
        services = self.client.domain_hosting_services.all()
        self.assertIn(self.service, services)

    def test_cascade_delete(self):
        invoice = DomainHostingInvoice.objects.create(
            service=self.service, invoice_date=date(2024, 6, 1),
            amount=Decimal('500.00'),
        )
        service_pk = self.service.pk
        self.service.delete()
        self.assertFalse(DomainHostingInvoice.objects.filter(service_id=service_pk).exists())


class DomainHostingInvoiceModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.client = Client.objects.create(
            company_name='Acme Corp', contact_person='Mr. X',
            email='acme@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        self.service = DomainHosting.objects.create(
            client=self.client, service_type='domain',
            service_name='example.com',
            registration_date=date(2024, 1, 1),
            expiry_date=date(2025, 12, 31),
        )
        self.invoice = DomainHostingInvoice.objects.create(
            service=self.service, invoice_number='INV-001',
            invoice_date=date(2024, 6, 1), amount=Decimal('500.00'),
        )

    def test_str(self):
        self.assertEqual(str(self.invoice), 'example.com — 2024-06-01')

    def test_defaults(self):
        self.assertFalse(self.invoice.paid)
        self.assertEqual(self.invoice.invoice_number, 'INV-001')

    def test_ordering(self):
        DomainHostingInvoice.objects.create(
            service=self.service, invoice_date=date(2024, 1, 1),
            amount=Decimal('100.00'),
        )
        dates = list(DomainHostingInvoice.objects.values_list('invoice_date', flat=True))
        self.assertEqual(dates, [date(2024, 6, 1), date(2024, 1, 1)])


# ---------------------------------------------------------------------------
# Form Tests
# ---------------------------------------------------------------------------

class DomainHostingFormTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.active_client = Client.objects.create(
            company_name='Acme Corp', contact_person='Mr. X',
            email='acme@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
            is_active=True,
        )
        self.inactive_client = Client.objects.create(
            company_name='Old Corp', contact_person='Mr. Y',
            email='old@test.com', phone='456', address='addr2',
            city=self.city, state=self.state, pincode='400002',
            is_active=False,
        )

    def test_valid_form(self):
        form = DomainHostingForm(data={
            'client': self.active_client.pk,
            'service_type': 'domain',
            'service_name': '  Example.COM  ',
            'provider': 'GoDaddy',
            'registration_date': '2024-01-01',
            'expiry_date': '2025-12-31',
            'renewal_amount': '1500.00',
            'gst_percent': '18.00',
            'status': 'active',
            'nameserver': '',
            'ip_address': '',
            'notes': '',
            'is_active': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_service_name_cleaning(self):
        form = DomainHostingForm(data={
            'client': self.active_client.pk,
            'service_type': 'domain',
            'service_name': '  Example.COM  ',
            'registration_date': '2024-01-01',
            'expiry_date': '2025-12-31',
            'renewal_amount': '0',
            'gst_percent': '18',
            'status': 'active',
        })
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEqual(instance.service_name, 'example.com')

    def test_client_queryset_active_only(self):
        form = DomainHostingForm()
        client_ids = list(form.fields['client'].queryset.values_list('pk', flat=True))
        self.assertIn(self.active_client.pk, client_ids)
        self.assertNotIn(self.inactive_client.pk, client_ids)

    def test_required_fields(self):
        form = DomainHostingForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('client', form.errors)
        self.assertIn('service_type', form.errors)
        self.assertIn('service_name', form.errors)
        self.assertIn('registration_date', form.errors)
        self.assertIn('expiry_date', form.errors)

    def test_optional_fields(self):
        form = DomainHostingForm(data={
            'client': self.active_client.pk,
            'service_type': 'domain',
            'service_name': 'test.com',
            'registration_date': '2024-01-01',
            'expiry_date': '2025-12-31',
            'provider': '',
            'nameserver': '',
            'ip_address': '',
            'notes': '',
            'renewal_amount': '0',
            'gst_percent': '18',
            'status': 'active',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_ip_address(self):
        form = DomainHostingForm(data={
            'client': self.active_client.pk,
            'service_type': 'domain',
            'service_name': 'test.com',
            'registration_date': '2024-01-01',
            'expiry_date': '2025-12-31',
            'ip_address': 'not-an-ip',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('ip_address', form.errors)


class DomainHostingInvoiceFormTest(TestCase):
    def test_valid_form(self):
        form = DomainHostingInvoiceForm(data={
            'invoice_number': 'INV-001',
            'invoice_date': '2024-06-01',
            'amount': '500.00',
            'paid': False,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_required_fields(self):
        form = DomainHostingInvoiceForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('invoice_date', form.errors)
        self.assertIn('amount', form.errors)

    def test_optional_fields(self):
        form = DomainHostingInvoiceForm(data={
            'invoice_date': '2024-06-01',
            'amount': '500.00',
            'invoice_number': '',
            'paid_date': None,
            'notes': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
