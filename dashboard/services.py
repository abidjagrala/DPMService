from datetime import timedelta
from collections import Counter

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from assets.models import Asset
from clients.models import Client, Employee, Homeworker
from comments.models import Comment
from hosting.models import DomainHosting
from network.models import NetworkDevice
from tickets.models import ServiceTicket

User = get_user_model()
today = timezone.now().date()
thirty_days = today + timedelta(days=30)
fifteen_days = today + timedelta(days=15)
seven_days = today + timedelta(days=7)


def _client_ticket_qs(user):
    """Return ServiceTicket queryset scoped to a client user, or all for staff."""
    qs = ServiceTicket.objects.filter(is_active=True)
    if user.is_client:
        qs = qs.filter(client__user=user)
    return qs


def apply_filters(qs, request):
    """Apply common dashboard filters to a queryset."""
    client_id = request.GET.get('client', '')
    state_id = request.GET.get('state', '')
    city_id = request.GET.get('city', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if client_id:
        qs = qs.filter(client_id=client_id)
    if state_id:
        qs = qs.filter(client__state_id=state_id)
    if city_id:
        qs = qs.filter(client__city_id=city_id)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


# ---------------------------------------------------------------------------
# KPI Counts
# ---------------------------------------------------------------------------

def _is_restricted(user):
    """Staff and client users have restricted dashboard access."""
    return user and (user.is_client or user.is_staff_member)


def get_entity_counts(user=None):
    if user and user.is_client:
        return {
            'total_clients': 0,
            'total_employees': 0,
            'total_homeworkers': Homeworker.objects.filter(is_active=True, client__user=user).count(),
        }
    if _is_restricted(user):
        return {
            'total_clients': 0,
            'total_employees': 0,
            'total_homeworkers': 0,
        }
    return {
        'total_clients': Client.objects.filter(is_active=True).count(),
        'total_employees': Employee.objects.filter(is_active=True).count(),
        'total_homeworkers': Homeworker.objects.filter(is_active=True).count(),
    }


def get_ticket_counts(user=None):
    tickets = _client_ticket_qs(user)
    return {
        'total_tickets': tickets.count(),
        'open_tickets': tickets.filter(status='new').count(),
        'in_progress_tickets': tickets.filter(status='in_progress').count(),
        'completed_tickets': tickets.filter(status='completed').count(),
        'tickets_today': tickets.filter(created_at__date=today).count(),
    }


def get_asset_counts(user=None):
    if _is_restricted(user):
        zero = {
            'total_assets': 0,
            'assigned_assets': 0,
            'available_assets': 0,
            'maintenance_assets': 0,
        }
        if user.is_client:
            assets = Asset.objects.filter(is_active=True, client__user=user)
            return {
                'total_assets': assets.count(),
                'assigned_assets': assets.filter(status='assigned').count(),
                'available_assets': assets.filter(status='available').count(),
                'maintenance_assets': assets.filter(status='in_repair').count(),
            }
        return zero
    assets = Asset.objects.filter(is_active=True)
    return {
        'total_assets': assets.count(),
        'assigned_assets': assets.filter(status='assigned').count(),
        'available_assets': assets.filter(status='available').count(),
        'maintenance_assets': assets.filter(status='in_repair').count(),
    }


def get_device_counts(user=None):
    if _is_restricted(user):
        return {
            'total_devices': 0,
            'active_devices': 0,
            'offline_devices': 0,
            'repair_devices': 0,
        }
    devices = NetworkDevice.objects.filter(is_active=True)
    return {
        'total_devices': devices.count(),
        'active_devices': devices.count(),
        'offline_devices': 0,
        'repair_devices': 0,
    }


def get_domain_hosting_counts(user=None):
    if _is_restricted(user):
        return {
            'total_domains': 0,
            'active_domains': 0,
            'expiring_domains_30': 0,
            'total_hosting': 0,
            'active_hosting': 0,
            'expiring_hosting_30': 0,
        }
    services = DomainHosting.objects.filter(is_active=True)
    domains = services.filter(service_type='domain')
    hosting = services.filter(service_type='hosting')
    return {
        'total_domains': domains.count(),
        'active_domains': domains.filter(status='active').count(),
        'expiring_domains_30': domains.filter(
            status='active', expiry_date__lte=thirty_days, expiry_date__gte=today
        ).count(),
        'total_hosting': hosting.count(),
        'active_hosting': hosting.filter(status='active').count(),
        'expiring_hosting_30': hosting.filter(
            status='active', expiry_date__lte=thirty_days, expiry_date__gte=today
        ).count(),
    }


def get_all_kpis(user=None):
    kpis = {}
    kpis.update(get_entity_counts(user))
    kpis.update(get_ticket_counts(user))
    kpis.update(get_asset_counts(user))
    kpis.update(get_device_counts(user))
    kpis.update(get_domain_hosting_counts(user))
    return kpis


# ---------------------------------------------------------------------------
# Chart Data
# ---------------------------------------------------------------------------

def get_monthly_ticket_trend(user=None):
    """Last 12 months: open, completed, total per month."""
    months = []
    now = timezone.now()
    for i in range(11, -1, -1):
        d = (now - timedelta(days=30 * i)).date()
        months.append({
            'label': d.strftime('%b %Y'),
            'year': d.year,
            'month': d.month,
        })

    tickets = _client_ticket_qs(user)
    result = {'labels': [], 'open': [], 'completed': [], 'total': []}

    for m in months:
        start = timezone.datetime(m['year'], m['month'], 1, tzinfo=timezone.utc)
        if m['month'] == 12:
            end = timezone.datetime(m['year'] + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = timezone.datetime(m['year'], m['month'] + 1, 1, tzinfo=timezone.utc)

        month_tickets = tickets.filter(created_at__gte=start, created_at__lt=end)
        result['labels'].append(m['label'])
        result['open'].append(month_tickets.filter(status='new').count())
        result['completed'].append(month_tickets.filter(status='completed').count())
        result['total'].append(month_tickets.count())

    return result


def get_tickets_by_status(user=None):
    """Pie chart data for ticket statuses."""
    tickets = _client_ticket_qs(user)
    data = tickets.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    labels = []
    values = []
    status_map = dict(ServiceTicket.Status.choices)
    for row in data:
        labels.append(status_map.get(row['status'], row['status']))
        values.append(row['count'])
    return {'labels': labels, 'values': values}


def get_client_wise_tickets(user=None):
    """Top 10 clients by ticket volume (horizontal bar)."""
    tickets = _client_ticket_qs(user)
    data = tickets.values(
        'client__company_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    return {
        'labels': [r['client__company_name'] for r in data],
        'values': [r['count'] for r in data],
    }


def get_staff_productivity(user=None):
    """Assigned vs completed tickets per staff member."""
    tickets = _client_ticket_qs(user)
    data = tickets.filter(
        assigned_to__isnull=False
    ).values(
        'assigned_to__user__first_name', 'assigned_to__user__last_name'
    ).annotate(
        assigned=Count('id'),
        completed=Count('id', filter=Q(status='completed'))
    ).order_by('-assigned')[:10]

    labels = []
    for r in data:
        name = f"{r['assigned_to__user__first_name']} {r['assigned_to__user__last_name']}".strip()
        labels.append(name or 'Unknown')

    return {
        'labels': labels,
        'assigned': [r['assigned'] for r in data],
        'completed': [r['completed'] for r in data],
    }


def get_asset_status_distribution(user=None):
    """Pie chart of asset statuses."""
    if _is_restricted(user):
        if user.is_client:
            data = Asset.objects.filter(is_active=True, client__user=user).values('status').annotate(
                count=Count('id')
            ).order_by('status')
            status_map = dict(Asset.Status.choices)
            return {
                'labels': [status_map.get(r['status'], r['status']) for r in data],
                'values': [r['count'] for r in data],
            }
        return {'labels': [], 'values': []}
    data = Asset.objects.filter(is_active=True).values('status').annotate(
        count=Count('id')
    ).order_by('status')
    status_map = dict(Asset.Status.choices)
    return {
        'labels': [status_map.get(r['status'], r['status']) for r in data],
        'values': [r['count'] for r in data],
    }


def get_device_category_distribution(user=None):
    """Bar chart of device types."""
    if _is_restricted(user):
        return {'labels': [], 'values': []}
    data = NetworkDevice.objects.filter(is_active=True).values('device_type').annotate(
        count=Count('id')
    ).order_by('device_type')
    type_map = dict(NetworkDevice.DeviceType.choices)
    return {
        'labels': [type_map.get(r['device_type'], r['device_type']) for r in data],
        'values': [r['count'] for r in data],
    }


def get_domain_hosting_overview(user=None):
    """Bar chart: active domains, expiring domains, active hosting, expiring hosting."""
    if _is_restricted(user):
        return {
            'labels': ['Active Domains', 'Expiring Domains', 'Active Hosting', 'Expiring Hosting'],
            'values': [0, 0, 0, 0],
        }
    services = DomainHosting.objects.filter(is_active=True)
    return {
        'labels': ['Active Domains', 'Expiring Domains', 'Active Hosting', 'Expiring Hosting'],
        'values': [
            services.filter(service_type='domain', status='active').count(),
            services.filter(service_type='domain', status='active', expiry_date__lte=thirty_days, expiry_date__gte=today).count(),
            services.filter(service_type='hosting', status='active').count(),
            services.filter(service_type='hosting', status='active', expiry_date__lte=thirty_days, expiry_date__gte=today).count(),
        ],
    }


def get_client_state_distribution(user=None):
    """Pie chart: clients by state."""
    if _is_restricted(user):
        return {'labels': [], 'values': []}
    data = Client.objects.filter(is_active=True).values(
        'state__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    return {
        'labels': [r['state__name'] or 'Unknown' for r in data],
        'values': [r['count'] for r in data],
    }


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

def get_recent_tickets(user=None, limit=15):
    tickets = ServiceTicket.objects.select_related(
        'client', 'assigned_to__user', 'service_type', 'asset'
    ).filter(is_active=True)
    if user.is_client:
        tickets = tickets.filter(client__user=user)
    return tickets.order_by('-updated_at')[:limit]


def get_recent_activities(user=None, limit=25):
    """Combine ticket history, notifications, and asset assignments into a timeline."""
    from notifications.models import Notification
    activities = []

    from tickets.models import TicketHistory
    history_qs = TicketHistory.objects.select_related('ticket', 'changed_by')
    if user.is_client:
        history_qs = history_qs.filter(ticket__client__user=user)
    elif user.is_staff_member:
        history_qs = history_qs.filter(ticket__assigned_to__user=user)
    for h in history_qs.order_by('-changed_at')[:limit]:
        activities.append({
            'verb': f'Ticket {h.ticket.ticket_number}: {h.field_changed} changed',
            'actor': h.changed_by.get_full_name() if h.changed_by else 'System',
            'created_at': h.changed_at,
            'level': 'info',
        })

    for n in Notification.objects.select_related('actor').filter(recipient=user).order_by('-created_at')[:limit]:
        activities.append({
            'verb': n.verb,
            'actor': n.actor.get_full_name() if n.actor else 'System',
            'created_at': n.created_at,
            'level': n.level,
        })

    activities.sort(key=lambda x: x['created_at'], reverse=True)
    return activities[:limit]


def get_expiry_alerts(user=None):
    """Domains and hosting expiring in 30/15/7 days."""
    if _is_restricted(user):
        return {
            'domains_30': DomainHosting.objects.none(),
            'domains_15': DomainHosting.objects.none(),
            'domains_7': DomainHosting.objects.none(),
            'hosting_30': DomainHosting.objects.none(),
            'hosting_15': DomainHosting.objects.none(),
            'hosting_7': DomainHosting.objects.none(),
        }
    services = DomainHosting.objects.filter(is_active=True, status='active').select_related('client')
    return {
        'domains_30': services.filter(service_type='domain', expiry_date__lte=thirty_days, expiry_date__gte=today),
        'domains_15': services.filter(service_type='domain', expiry_date__lte=fifteen_days, expiry_date__gte=today),
        'domains_7': services.filter(service_type='domain', expiry_date__lte=seven_days, expiry_date__gte=today),
        'hosting_30': services.filter(service_type='hosting', expiry_date__lte=thirty_days, expiry_date__gte=today),
        'hosting_15': services.filter(service_type='hosting', expiry_date__lte=fifteen_days, expiry_date__gte=today),
        'hosting_7': services.filter(service_type='hosting', expiry_date__lte=seven_days, expiry_date__gte=today),
    }


def get_asset_warranty_alerts(user=None):
    """Assets with warranty expiring within 30 days."""
    if _is_restricted(user):
        if user.is_client:
            return Asset.objects.filter(
                is_active=True,
                client__user=user,
                warranty_expiry__lte=thirty_days,
                warranty_expiry__gte=today,
            ).select_related('asset_type', 'client')[:10]
        return Asset.objects.none()
    return Asset.objects.filter(
        is_active=True,
        warranty_expiry__lte=thirty_days,
        warranty_expiry__gte=today,
    ).select_related('asset_type', 'client')[:10]


def get_client_summary(user=None):
    """Top 10 clients with homeworker/asset/ticket counts."""
    if _is_restricted(user):
        if user.is_client:
            client = Client.objects.filter(user=user).first()
            if client:
                return Client.objects.filter(pk=client.pk).annotate(
                    homeworker_count=Count('homeworkers', filter=Q(homeworkers__is_active=True)),
                    asset_count=Count('assets', filter=Q(assets__is_active=True)),
                    open_ticket_count=Count(
                        'service_tickets', filter=Q(service_tickets__status__in=['new', 'assigned', 'in_progress'])
                    ),
                )
        return Client.objects.none()
    clients = Client.objects.filter(is_active=True).annotate(
        homeworker_count=Count('homeworkers', filter=Q(homeworkers__is_active=True)),
        asset_count=Count('assets', filter=Q(assets__is_active=True)),
        open_ticket_count=Count(
            'service_tickets', filter=Q(service_tickets__status__in=['new', 'assigned', 'in_progress'])
        ),
    ).order_by('-open_ticket_count')[:10]
    return clients


def get_homeworker_summary(user=None):
    """Global homeworker stats."""
    if _is_restricted(user):
        if user.is_client:
            hw = Homeworker.objects.filter(is_active=True, client__user=user)
            open_tickets = ServiceTicket.objects.filter(
                is_active=True, status__in=['new', 'assigned', 'in_progress'], client__user=user
            ).count()
            closed_tickets = ServiceTicket.objects.filter(
                is_active=True, status='completed', client__user=user
            ).count()
            return {
                'total': hw.count(),
                'assigned_assets': Asset.objects.filter(homeworker__isnull=False, is_active=True, client__user=user).count(),
                'assigned_devices': NetworkDevice.objects.filter(homeworker__isnull=False, is_active=True, client__user=user).count(),
                'open_tickets': open_tickets,
                'closed_tickets': closed_tickets,
            }
        return {
            'total': 0,
            'assigned_assets': 0,
            'assigned_devices': 0,
            'open_tickets': 0,
            'closed_tickets': 0,
        }
    hw = Homeworker.objects.filter(is_active=True)
    return {
        'total': hw.count(),
        'assigned_assets': Asset.objects.filter(homeworker__isnull=False, is_active=True).count(),
        'assigned_devices': NetworkDevice.objects.filter(homeworker__isnull=False, is_active=True).count(),
        'open_tickets': ServiceTicket.objects.filter(
            is_active=True, status__in=['new', 'assigned', 'in_progress']
        ).count(),
        'closed_tickets': ServiceTicket.objects.filter(
            is_active=True, status='completed'
        ).count(),
    }


def get_domain_hosting_panel(user=None):
    """Domains and hosting for the panel table."""
    if _is_restricted(user):
        return {
            'domains': DomainHosting.objects.none(),
            'hosting': DomainHosting.objects.none(),
        }
    services = DomainHosting.objects.filter(is_active=True).select_related('client').order_by('expiry_date')
    return {
        'domains': services.filter(service_type='domain')[:10],
        'hosting': services.filter(service_type='hosting')[:10],
    }


def get_my_tasks(user):
    """Tasks for logged-in staff or client tickets."""
    if user.is_client:
        tickets = ServiceTicket.objects.filter(
            client__user=user, is_active=True
        ).exclude(status__in=['completed', 'cancelled'])
        return {
            'assigned_tickets': tickets.select_related('client', 'service_type')[:10],
            'pending_count': tickets.filter(status__in=['new', 'assigned']).count(),
            'due_today_count': tickets.filter(scheduled_date=today).count(),
            'overdue_count': tickets.filter(
                scheduled_date__lt=today
            ).exclude(status__in=['completed', 'cancelled']).count(),
        }
    if not hasattr(user, 'employee_profile'):
        return {
            'assigned_tickets': ServiceTicket.objects.none(),
            'pending_count': 0,
            'due_today_count': 0,
            'overdue_count': 0,
        }
    emp = user.employee_profile
    assigned = ServiceTicket.objects.filter(
        assigned_to=emp, is_active=True
    ).exclude(status__in=['completed', 'cancelled'])
    return {
        'assigned_tickets': assigned.select_related('client', 'service_type')[:10],
        'pending_count': assigned.filter(status__in=['new', 'assigned']).count(),
        'due_today_count': assigned.filter(scheduled_date=today).count(),
        'overdue_count': assigned.filter(
            scheduled_date__lt=today
        ).exclude(status__in=['completed', 'cancelled']).count(),
    }


def get_recent_comments(user=None, limit=15):
    qs = Comment.objects.select_related(
        'created_by', 'content_type'
    )
    if user and user.is_client:
        qs = qs.filter(content_type__model='serviceticket', object_id__in=ServiceTicket.objects.filter(client__user=user).values_list('id', flat=True))
    return qs.order_by('-created_at')[:limit]
