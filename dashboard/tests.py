from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.utils import timezone

from assets.models import Asset
from clients.models import Client, Employee, Homeworker
from comments.models import Comment
from hosting.models import DomainHosting
from masters.models import AssetType, City, ServiceType, State
from tickets.models import ServiceTicket, TicketHistory

from .services import (
    _client_ticket_qs, apply_filters, _is_restricted,
    get_entity_counts, get_ticket_counts, get_asset_counts,
    get_domain_hosting_counts, get_all_kpis,
    get_tickets_by_status, get_client_wise_tickets,
    get_asset_status_distribution, get_client_state_distribution,
    get_recent_tickets, get_recent_activities, get_expiry_alerts,
    get_client_summary, get_homeworker_summary,
    get_my_tasks, get_recent_comments,
)

User = get_user_model()


class BaseDashboardTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.service_type = ServiceType.objects.create(name='Pickup')
        self.asset_type = AssetType.objects.create(name='Laptop')

        self.admin = User.objects.create_superuser(email='admin@t.com', password='pass123')
        self.staff_user = User.objects.create_user(email='staff@t.com', password='pass123', role='staff')
        self.client_user = User.objects.create_user(email='client@t.com', password='pass123', role='client')
        self.manager = User.objects.create_manager(email='mgr@t.com', password='pass123')

        self.client_obj = Client.objects.create(
            user=self.client_user,
            company_name='Acme Corp', contact_person='Mr. X',
            email='acme@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        self.client_user.client_profile = self.client_obj
        self.client_user.save()

        self.employee_user = User.objects.create_user(email='emp@t.com', password='pass123', role='staff')
        self.employee = Employee.objects.create(
            user=self.employee_user, employee_id='EMP001',
            designation='Technician', phone='999',
        )

        self.ticket = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client_obj, subject='Test ticket',
            priority='high', status='new', created_by=self.admin,
        )


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------

class IsRestrictedTest(BaseDashboardTest):
    def test_admin_not_restricted(self):
        self.assertFalse(_is_restricted(self.admin))

    def test_manager_not_restricted(self):
        self.assertFalse(_is_restricted(self.manager))

    def test_staff_restricted(self):
        self.assertTrue(_is_restricted(self.staff_user))

    def test_client_restricted(self):
        self.assertTrue(_is_restricted(self.client_user))


class ClientTicketQsTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        self.ticket2 = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client_obj, subject='Another ticket',
            created_by=self.admin,
        )

    def test_admin_gets_all_tickets(self):
        qs = _client_ticket_qs(self.admin)
        self.assertEqual(qs.count(), 2)

    def test_client_gets_own_tickets(self):
        qs = _client_ticket_qs(self.client_user)
        self.assertEqual(qs.count(), 2)

    def test_staff_gets_all_tickets(self):
        qs = _client_ticket_qs(self.staff_user)
        self.assertEqual(qs.count(), 2)


class ApplyFiltersTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        self.ticket2 = ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client_obj, subject='Second',
            created_by=self.admin,
        )

    def _make_request(self, params):
        request = self.factory.get('/dashboard/', params)
        return request

    def test_no_filters(self):
        qs = ServiceTicket.objects.filter(is_active=True)
        request = self._make_request({})
        result = apply_filters(qs, request)
        self.assertEqual(result.count(), 2)

    def test_filter_by_client(self):
        other_client = Client.objects.create(
            company_name='Other', contact_person='Mr. Y',
            email='other@test.com', phone='456', address='addr2',
            city=self.city, state=self.state, pincode='400002',
        )
        ServiceTicket.objects.create(
            service_type=self.service_type,
            client=other_client, subject='Other ticket',
            created_by=self.admin,
        )
        qs = ServiceTicket.objects.filter(is_active=True)
        request = self._make_request({'client': self.client_obj.pk})
        result = apply_filters(qs, request)
        self.assertEqual(result.count(), 2)

    def test_filter_by_date_from(self):
        qs = ServiceTicket.objects.filter(is_active=True)
        future = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        request = self._make_request({'date_from': future})
        result = apply_filters(qs, request)
        self.assertEqual(result.count(), 0)

    def test_filter_by_date_to(self):
        qs = ServiceTicket.objects.filter(is_active=True)
        past = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        request = self._make_request({'date_to': past})
        result = apply_filters(qs, request)
        self.assertEqual(result.count(), 0)


# ---------------------------------------------------------------------------
# KPI Count Tests
# ---------------------------------------------------------------------------

class EntityCountsTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        self.hw = Homeworker.objects.create(
            client=self.client_obj, name='HW One',
            phone='111', address='addr', pincode='400001',
        )

    def test_admin_sees_all(self):
        counts = get_entity_counts(self.admin)
        self.assertEqual(counts['total_clients'], 1)
        self.assertEqual(counts['total_employees'], 1)
        self.assertEqual(counts['total_homeworkers'], 1)

    def test_client_sees_own_homeworkers(self):
        counts = get_entity_counts(self.client_user)
        self.assertEqual(counts['total_clients'], 0)
        self.assertEqual(counts['total_employees'], 0)
        self.assertEqual(counts['total_homeworkers'], 1)

    def test_staff_restricted(self):
        counts = get_entity_counts(self.staff_user)
        self.assertEqual(counts['total_clients'], 0)
        self.assertEqual(counts['total_employees'], 0)
        self.assertEqual(counts['total_homeworkers'], 0)


class TicketCountsTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client_obj, subject='Open',
            status='new', created_by=self.admin,
        )
        ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client_obj, subject='Progress',
            status='in_progress', created_by=self.admin,
        )
        ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client_obj, subject='Done',
            status='completed', created_by=self.admin,
        )

    def test_ticket_counts(self):
        counts = get_ticket_counts(self.admin)
        self.assertEqual(counts['total_tickets'], 4)
        self.assertEqual(counts['open_tickets'], 2)
        self.assertEqual(counts['in_progress_tickets'], 1)
        self.assertEqual(counts['completed_tickets'], 1)


class AssetCountsTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        Asset.objects.create(
            asset_tag='AST-001', asset_type=self.asset_type,
            brand_model='Dell Latitude',
            status='assigned', client=self.client_obj,
        )
        Asset.objects.create(
            asset_tag='AST-002', asset_type=self.asset_type,
            brand_model='HP EliteBook',
            status='available',
        )

    def test_admin_sees_all_assets(self):
        counts = get_asset_counts(self.admin)
        self.assertEqual(counts['total_assets'], 2)
        self.assertEqual(counts['assigned_assets'], 1)
        self.assertEqual(counts['available_assets'], 1)

    def test_client_sees_own_assets(self):
        counts = get_asset_counts(self.client_user)
        self.assertEqual(counts['total_assets'], 1)
        self.assertEqual(counts['assigned_assets'], 1)

    def test_staff_restricted(self):
        counts = get_asset_counts(self.staff_user)
        self.assertEqual(counts['total_assets'], 0)


class DomainHostingCountsTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        DomainHosting.objects.create(
            client=self.client_obj, service_type='domain',
            service_name='example.com',
            registration_date=date(2024, 1, 1),
            expiry_date=date.today() + timedelta(days=15),
        )
        DomainHosting.objects.create(
            client=self.client_obj, service_type='hosting',
            service_name='hosting.example.com',
            registration_date=date(2024, 1, 1),
            expiry_date=date.today() + timedelta(days=5),
        )

    def test_admin_sees_all(self):
        counts = get_domain_hosting_counts(self.admin)
        self.assertEqual(counts['total_domains'], 1)
        self.assertEqual(counts['active_domains'], 1)
        self.assertEqual(counts['total_hosting'], 1)
        self.assertEqual(counts['active_hosting'], 1)

    def test_expiring_counts(self):
        counts = get_domain_hosting_counts(self.admin)
        self.assertEqual(counts['expiring_domains_30'], 1)
        self.assertEqual(counts['expiring_hosting_30'], 1)

    def test_restricted_returns_zeros(self):
        counts = get_domain_hosting_counts(self.staff_user)
        self.assertEqual(counts['total_domains'], 0)


class AllKpisTest(BaseDashboardTest):
    def test_all_kpis_merges(self):
        kpis = get_all_kpis(self.admin)
        self.assertIn('total_clients', kpis)
        self.assertIn('total_tickets', kpis)
        self.assertIn('total_assets', kpis)
        self.assertIn('total_domains', kpis)


# ---------------------------------------------------------------------------
# Chart Data Tests
# ---------------------------------------------------------------------------

class TicketsByStatusTest(BaseDashboardTest):
    def test_returns_labels_and_values(self):
        data = get_tickets_by_status(self.admin)
        self.assertIn('labels', data)
        self.assertIn('values', data)
        self.assertEqual(len(data['labels']), len(data['values']))

    def test_includes_statuses(self):
        ServiceTicket.objects.create(
            service_type=self.service_type,
            client=self.client_obj, subject='Done',
            status='completed', created_by=self.admin,
        )
        data = get_tickets_by_status(self.admin)
        statuses = set(data['values'])
        self.assertTrue(len(data['labels']) > 0)


class ClientWiseTicketsTest(BaseDashboardTest):
    def test_top_10_ordering(self):
        data = get_client_wise_tickets(self.admin)
        self.assertIn('labels', data)
        self.assertIn('values', data)
        if data['values']:
            self.assertEqual(data['labels'][0], 'Acme Corp')


class AssetStatusDistributionTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        Asset.objects.create(
            asset_tag='AST-001', asset_type=self.asset_type,
            brand_model='Dell XPS', status='available',
        )

    def test_admin_sees_assets(self):
        data = get_asset_status_distribution(self.admin)
        self.assertTrue(len(data['labels']) > 0)

    def test_staff_returns_empty(self):
        data = get_asset_status_distribution(self.staff_user)
        self.assertEqual(data['labels'], [])


class ClientStateDistributionTest(BaseDashboardTest):
    def test_returns_state_data(self):
        data = get_client_state_distribution(self.admin)
        self.assertIn('labels', data)
        self.assertIn('MH', data['labels'])

    def test_restricted_returns_empty(self):
        data = get_client_state_distribution(self.staff_user)
        self.assertEqual(data['labels'], [])


# ---------------------------------------------------------------------------
# Panel Function Tests
# ---------------------------------------------------------------------------

class RecentTicketsTest(BaseDashboardTest):
    def test_returns_tickets(self):
        tickets = get_recent_tickets(self.admin)
        self.assertEqual(tickets.count(), 1)

    def test_client_scoped(self):
        tickets = get_recent_tickets(self.client_user)
        self.assertEqual(tickets.count(), 1)


class RecentActivitiesTest(BaseDashboardTest):
    def test_returns_activities(self):
        TicketHistory.objects.create(
            ticket=self.ticket, field_changed='status',
            old_value='new', new_value='assigned',
            changed_by=self.admin,
        )
        activities = get_recent_activities(self.admin)
        self.assertTrue(len(activities) > 0)


class ExpiryAlertsTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        self.expiring_domain = DomainHosting.objects.create(
            client=self.client_obj, service_type='domain',
            service_name='expire-soon.com',
            registration_date=date(2024, 1, 1),
            expiry_date=date.today() + timedelta(days=5),
        )

    def test_admin_sees_alerts(self):
        alerts = get_expiry_alerts(self.admin)
        self.assertIn('domains_30', alerts)
        self.assertIn('hosting_7', alerts)
        self.assertTrue(alerts['domains_30'].count() > 0)

    def test_restricted_returns_empty_querysets(self):
        alerts = get_expiry_alerts(self.staff_user)
        self.assertEqual(alerts['domains_30'].count(), 0)


class ClientSummaryTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        Homeworker.objects.create(
            client=self.client_obj, name='HW1',
            phone='111', address='addr', pincode='400001',
        )

    def test_admin_sees_summary(self):
        summary = get_client_summary(self.admin)
        self.assertTrue(summary.count() > 0)
        first = summary.first()
        self.assertEqual(first.homeworker_count, 1)

    def test_restricted_returns_empty(self):
        summary = get_client_summary(self.staff_user)
        self.assertEqual(summary.count(), 0)


class HomeworkerSummaryTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        self.hw = Homeworker.objects.create(
            client=self.client_obj, name='HW1',
            phone='111', address='addr', pincode='400001',
        )

    def test_admin_summary(self):
        summary = get_homeworker_summary(self.admin)
        self.assertEqual(summary['total'], 1)

    def test_client_summary(self):
        summary = get_homeworker_summary(self.client_user)
        self.assertEqual(summary['total'], 1)

    def test_staff_restricted(self):
        summary = get_homeworker_summary(self.staff_user)
        self.assertEqual(summary['total'], 0)


class MyTasksTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        self.ticket.scheduled_date = date.today()
        self.ticket.assigned_to = self.employee
        self.ticket.save()

    def test_employee_with_profile(self):
        tasks = get_my_tasks(self.employee_user)
        self.assertIn('assigned_tickets', tasks)
        self.assertIn('pending_count', tasks)
        self.assertIn('overdue_count', tasks)

    def test_employee_without_profile(self):
        no_profile_user = User.objects.create_user(
            email='nop@t.com', password='pass123', role='staff',
        )
        tasks = get_my_tasks(no_profile_user)
        self.assertEqual(tasks['pending_count'], 0)
        self.assertEqual(tasks['overdue_count'], 0)

    def test_client_tasks(self):
        tasks = get_my_tasks(self.client_user)
        self.assertIn('assigned_tickets', tasks)

    def test_overdue_detection(self):
        self.ticket.scheduled_date = date.today() - timedelta(days=1)
        self.ticket.save()
        tasks = get_my_tasks(self.employee_user)
        self.assertEqual(tasks['overdue_count'], 1)


class RecentCommentsTest(BaseDashboardTest):
    def setUp(self):
        super().setUp()
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(ServiceTicket)
        Comment.objects.create(
            content_type=ct, object_id=self.ticket.pk,
            body='Test comment', created_by=self.admin,
        )

    def test_returns_comments(self):
        comments = get_recent_comments(self.admin)
        self.assertEqual(comments.count(), 1)

    def test_client_scoped(self):
        comments = get_recent_comments(self.client_user)
        self.assertEqual(comments.count(), 1)
