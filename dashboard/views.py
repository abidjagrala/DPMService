import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx
from clients.models import Client
from masters.models import City, State

from . import services

logger = logging.getLogger(__name__)


def _safe(fn, default, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        logger.exception('Dashboard service error in %s', fn.__name__)
        return default


@login_required
@require_http_methods(['GET'])
def dashboard_view(request):
    user = request.user
    ctx = _safe(services.get_all_kpis, {
        'total_clients': 0, 'total_employees': 0, 'total_homeworkers': 0,
        'total_tickets': 0, 'open_tickets': 0, 'in_progress_tickets': 0,
        'completed_tickets': 0, 'tickets_today': 0,
        'total_assets': 0, 'assigned_assets': 0, 'available_assets': 0, 'maintenance_assets': 0,
        'total_devices': 0, 'active_devices': 0, 'offline_devices': 0, 'repair_devices': 0,
        'total_domains': 0, 'active_domains': 0, 'expiring_domains_30': 0,
        'total_hosting': 0, 'active_hosting': 0, 'expiring_hosting_30': 0,
    }, user)
    ctx['recent_tickets'] = _safe(services.get_recent_tickets, [], user)
    ctx['recent_activities'] = _safe(services.get_recent_activities, [], user)
    ctx['expiry_alerts'] = _safe(services.get_expiry_alerts, {
        'domains_30': [], 'domains_15': [], 'domains_7': [],
        'hosting_30': [], 'hosting_15': [], 'hosting_7': [],
    }, user)
    ctx['warranty_alerts'] = _safe(services.get_asset_warranty_alerts, [], user)
    ctx['client_summary'] = _safe(services.get_client_summary, Client.objects.none(), user)
    ctx['homeworker_summary'] = _safe(services.get_homeworker_summary, {
        'total': 0, 'assigned_assets': 0, 'assigned_devices': 0,
        'open_tickets': 0, 'closed_tickets': 0,
    }, user)
    ctx['domain_hosting_panel'] = _safe(services.get_domain_hosting_panel, {
        'domains': [], 'hosting': [],
    }, user)
    ctx['my_tasks'] = _safe(services.get_my_tasks, {
        'assigned_tickets': [], 'pending_count': 0,
        'due_today_count': 0, 'overdue_count': 0,
    }, user)
    ctx['recent_comments'] = _safe(services.get_recent_comments, [], user)

    # Filter options
    if user.is_client:
        ctx['clients'] = Client.objects.filter(user=user)
    else:
        ctx['clients'] = Client.objects.filter(is_active=True)
    ctx['states'] = State.objects.filter(is_active=True)
    ctx['cities'] = City.objects.filter(is_active=True)

    ctx['page_title'] = 'Dashboard'
    return render(request, 'dashboard/dashboard.html', ctx)


# ---------------------------------------------------------------------------
# HTMX partials — each returns only its section
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def dashboard_kpis(request):
    empty = {
        'total_clients': 0, 'total_employees': 0, 'total_homeworkers': 0,
        'total_tickets': 0, 'open_tickets': 0, 'in_progress_tickets': 0,
        'completed_tickets': 0, 'tickets_today': 0,
        'total_assets': 0, 'assigned_assets': 0, 'available_assets': 0, 'maintenance_assets': 0,
        'total_devices': 0, 'active_devices': 0, 'offline_devices': 0, 'repair_devices': 0,
        'total_domains': 0, 'active_domains': 0, 'expiring_domains_30': 0,
        'total_hosting': 0, 'active_hosting': 0, 'expiring_hosting_30': 0,
    }
    return render(request, 'dashboard/_kpi_cards.html', _safe(services.get_all_kpis, empty, request.user))


@login_required
@require_http_methods(['GET'])
def dashboard_charts(request):
    user = request.user
    empty = {'labels': [], 'values': []}
    ctx = {
        'monthly_trend': _safe(services.get_monthly_ticket_trend, {'labels': [], 'open': [], 'completed': [], 'total': []}, user),
        'tickets_by_status': _safe(services.get_tickets_by_status, empty, user),
        'client_wise_tickets': _safe(services.get_client_wise_tickets, empty, user),
        'staff_productivity': _safe(services.get_staff_productivity, {'labels': [], 'assigned': [], 'completed': []}, user),
        'asset_status': _safe(services.get_asset_status_distribution, empty, user),
        'device_categories': _safe(services.get_device_category_distribution, empty, user),
        'domain_hosting_overview': _safe(services.get_domain_hosting_overview, empty, user),
        'client_state_dist': _safe(services.get_client_state_distribution, empty, user),
    }
    return render(request, 'dashboard/_charts.html', ctx)


@login_required
@require_http_methods(['GET'])
def dashboard_recent_tickets(request):
    return render(request, 'dashboard/_recent_tickets.html', {
        'recent_tickets': _safe(services.get_recent_tickets, [], request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_activities(request):
    return render(request, 'dashboard/_activities.html', {
        'recent_activities': _safe(services.get_recent_activities, [], request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_expiry_alerts(request):
    return render(request, 'dashboard/_expiry_alerts.html', {
        'expiry_alerts': _safe(services.get_expiry_alerts, {
            'domains_30': [], 'domains_15': [], 'domains_7': [],
            'hosting_30': [], 'hosting_15': [], 'hosting_7': [],
        }, request.user),
        'warranty_alerts': _safe(services.get_asset_warranty_alerts, [], request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_client_summary(request):
    return render(request, 'dashboard/_client_summary.html', {
        'client_summary': _safe(services.get_client_summary, Client.objects.none(), request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_homeworker_summary(request):
    return render(request, 'dashboard/_homeworker_summary.html', {
        'homeworker_summary': _safe(services.get_homeworker_summary, {
            'total': 0, 'assigned_assets': 0, 'assigned_devices': 0,
            'open_tickets': 0, 'closed_tickets': 0,
        }, request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_domain_hosting(request):
    return render(request, 'dashboard/_domain_hosting_panel.html', {
        'domain_hosting_panel': _safe(services.get_domain_hosting_panel, {
            'domains': [], 'hosting': [],
        }, request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_my_tasks(request):
    return render(request, 'dashboard/_my_tasks.html', {
        'my_tasks': _safe(services.get_my_tasks, {
            'assigned_tickets': [], 'pending_count': 0,
            'due_today_count': 0, 'overdue_count': 0,
        }, request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_comments(request):
    return render(request, 'dashboard/_recent_comments.html', {
        'recent_comments': _safe(services.get_recent_comments, [], request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_quick_actions(request):
    return render(request, 'dashboard/_quick_actions.html')


# ---------------------------------------------------------------------------
# Chart JSON API (for Chart.js fetch)
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def chart_monthly_trend(request):
    empty = {'labels': [], 'open': [], 'completed': [], 'total': []}
    return JsonResponse(_safe(services.get_monthly_ticket_trend, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_tickets_by_status(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_tickets_by_status, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_client_wise_tickets(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_client_wise_tickets, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_staff_productivity(request):
    empty = {'labels': [], 'assigned': [], 'completed': []}
    return JsonResponse(_safe(services.get_staff_productivity, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_asset_status(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_asset_status_distribution, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_device_categories(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_device_category_distribution, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_domain_hosting(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_domain_hosting_overview, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_client_state(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_client_state_distribution, empty, request.user))
