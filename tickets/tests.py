from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from clients.models import Client, Employee
from masters.models import City, ServiceType, State

from .models import ServiceTicket, TicketComment, TicketHistory

User = get_user_model()


class ServiceTicketModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.service_type = ServiceType.objects.create(name='Pickup')
        self.client = Client.objects.create(
            company_name='TCS', contact_person='Mr. K',
            email='tcs@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        self.user = User.objects.create_user(email='u@t.com', password='pass123')

    def test_create_ticket(self):
        ticket = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, priority='high',
            subject='Laptop pickup', created_by=self.user,
        )
        self.assertTrue(ticket.ticket_number.startswith('DPM'))
        self.assertEqual(ticket.status, 'new')
        self.assertEqual(str(ticket), f'{ticket.ticket_number} — Laptop pickup')

    def test_ticket_number_auto_generated(self):
        t1 = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, subject='T1', created_by=self.user,
        )
        t2 = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, subject='T2', created_by=self.user,
        )
        self.assertNotEqual(t1.ticket_number, t2.ticket_number)

    def test_is_overdue_true(self):
        ticket = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, subject='Overdue',
            scheduled_date=date.today() - timedelta(days=1),
            status='new', created_by=self.user,
        )
        self.assertTrue(ticket.is_overdue)

    def test_is_overdue_false_when_completed(self):
        ticket = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, subject='Done',
            scheduled_date=date.today() - timedelta(days=1),
            status='completed', created_by=self.user,
        )
        self.assertFalse(ticket.is_overdue)

    def test_is_overdue_false_no_date(self):
        ticket = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, subject='No date', created_by=self.user,
        )
        self.assertFalse(ticket.is_overdue)


class TicketCommentModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.service_type = ServiceType.objects.create(name='Pickup')
        self.client = Client.objects.create(
            company_name='TCS', contact_person='Mr. K',
            email='tcs@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        self.user = User.objects.create_user(email='u@t.com', password='pass123')
        self.ticket = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, subject='T1', created_by=self.user,
        )

    def test_create_comment(self):
        comment = TicketComment.objects.create(
            ticket=self.ticket, comment='Test comment',
            created_by=self.user,
        )
        self.assertIn(self.ticket.ticket_number, str(comment))

    def test_str_deleted_user(self):
        comment = TicketComment.objects.create(
            ticket=self.ticket, comment='Test', created_by=None,
        )
        self.assertIn('Unknown', str(comment))


class TicketHistoryModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.service_type = ServiceType.objects.create(name='Pickup')
        self.client = Client.objects.create(
            company_name='TCS', contact_person='Mr. K',
            email='tcs@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        self.user = User.objects.create_user(email='u@t.com', password='pass123')
        self.ticket = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client, subject='T1', created_by=self.user,
        )

    def test_create_history(self):
        history = TicketHistory.objects.create(
            ticket=self.ticket, field_changed='status',
            old_value='new', new_value='assigned',
            changed_by=self.user,
        )
        self.assertIn('status', str(history))
