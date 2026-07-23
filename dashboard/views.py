import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx
from clients.models import Client

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
    ctx = {}
    ctx['page_title'] = 'Dashboard'
    return render(request, 'dashboard/dashboard.html', ctx)


# ---------------------------------------------------------------------------
# HTMX partials — each returns only its section
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def dashboard_kpis(request):
    empty = {
        'total_clients': 0, 'total_employees': 0,
        'total_tickets': 0, 'open_tickets': 0, 'in_progress_tickets': 0,
        'completed_tickets': 0, 'tickets_today': 0,
        'total_assets': 0, 'assigned_assets': 0, 'available_assets': 0, 'maintenance_assets': 0,
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
def chart_domain_hosting(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_domain_hosting_overview, empty, request.user))


@login_required
@require_http_methods(['GET'])
def chart_client_state(request):
    empty = {'labels': [], 'values': []}
    return JsonResponse(_safe(services.get_client_state_distribution, empty, request.user))


# ---------------------------------------------------------------------------
# Tab partials
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def dashboard_tickets_tab(request):
    user = request.user
    empty_kpi = {
        'total_tickets': 0, 'open_tickets': 0, 'in_progress_tickets': 0,
        'completed_tickets': 0, 'tickets_today': 0,
    }
    ctx = _safe(services.get_ticket_counts, empty_kpi, user)
    ctx['recent_tickets'] = _safe(services.get_recent_tickets, [], user)[:10]
    ctx['recent_activities'] = _safe(services.get_recent_activities, [], user)
    ctx['my_tasks'] = _safe(services.get_my_tasks, {
        'assigned_tickets': [], 'pending_count': 0,
        'due_today_count': 0, 'overdue_count': 0,
    }, user)
    ctx['recent_comments'] = _safe(services.get_recent_comments, [], user)
    return render(request, 'dashboard/_tab_tickets.html', ctx)


@login_required
@require_http_methods(['GET'])
def dashboard_assets_tab(request):
    user = request.user
    empty_kpi = {
        'total_assets': 0, 'assigned_assets': 0,
        'available_assets': 0, 'maintenance_assets': 0,
    }
    ctx = _safe(services.get_asset_counts, empty_kpi, user)
    ctx['warranty_alerts'] = _safe(services.get_asset_warranty_alerts, [], user)
    return render(request, 'dashboard/_tab_assets.html', ctx)


@login_required
@require_http_methods(['GET'])
def dashboard_domain_hosting_tab(request):
    user = request.user
    empty_kpi = {
        'total_domains': 0, 'active_domains': 0, 'expiring_domains_30': 0,
        'total_hosting': 0, 'active_hosting': 0, 'expiring_hosting_30': 0,
    }
    ctx = _safe(services.get_domain_hosting_counts, empty_kpi, user)
    ctx['expired_dh_list'] = _safe(services.get_expired_domain_hosting_list, [], user)
    ctx['next_expiry_dh_list'] = _safe(services.get_next_expiry_domain_hosting_list, [], user)
    ctx['expiry_alerts'] = _safe(services.get_expiry_alerts, {
        'domains_30': [], 'domains_15': [], 'domains_7': [],
        'hosting_30': [], 'hosting_15': [], 'hosting_7': [],
    }, user)
    return render(request, 'dashboard/_tab_domain_hosting.html', ctx)


@login_required
@require_http_methods(['GET'])
def dashboard_others_tab(request):
    user = request.user
    ctx = _safe(services.get_entity_counts_with_status, {
        'total_clients': 0, 'active_clients': 0, 'inactive_clients': 0,
        'total_employees': 0, 'active_employees': 0, 'inactive_employees': 0,
    }, user)
    return render(request, 'dashboard/_tab_others.html', ctx)
