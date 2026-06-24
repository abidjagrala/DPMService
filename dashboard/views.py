import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx
from clients.models import Client
from masters.models import City, State

from . import services


@login_required
@require_http_methods(['GET'])
def dashboard_view(request):
    user = request.user
    ctx = services.get_all_kpis(user)
    ctx['recent_tickets'] = services.get_recent_tickets(user)
    ctx['recent_activities'] = services.get_recent_activities(user)
    ctx['expiry_alerts'] = services.get_expiry_alerts(user)
    ctx['warranty_alerts'] = services.get_asset_warranty_alerts(user)
    ctx['client_summary'] = services.get_client_summary(user)
    ctx['homeworker_summary'] = services.get_homeworker_summary(user)
    ctx['domain_hosting_panel'] = services.get_domain_hosting_panel(user)
    ctx['my_tasks'] = services.get_my_tasks(user)
    ctx['recent_comments'] = services.get_recent_comments(user)

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
    return render(request, 'dashboard/_kpi_cards.html', services.get_all_kpis(request.user))


@login_required
@require_http_methods(['GET'])
def dashboard_charts(request):
    user = request.user
    ctx = {
        'monthly_trend': services.get_monthly_ticket_trend(user),
        'tickets_by_status': services.get_tickets_by_status(user),
        'client_wise_tickets': services.get_client_wise_tickets(user),
        'staff_productivity': services.get_staff_productivity(user),
        'asset_status': services.get_asset_status_distribution(user),
        'device_categories': services.get_device_category_distribution(user),
        'domain_hosting_overview': services.get_domain_hosting_overview(user),
        'client_state_dist': services.get_client_state_distribution(user),
    }
    return render(request, 'dashboard/_charts.html', ctx)


@login_required
@require_http_methods(['GET'])
def dashboard_recent_tickets(request):
    return render(request, 'dashboard/_recent_tickets.html', {
        'recent_tickets': services.get_recent_tickets(request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_activities(request):
    return render(request, 'dashboard/_activities.html', {
        'recent_activities': services.get_recent_activities(request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_expiry_alerts(request):
    return render(request, 'dashboard/_expiry_alerts.html', {
        'expiry_alerts': services.get_expiry_alerts(request.user),
        'warranty_alerts': services.get_asset_warranty_alerts(request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_client_summary(request):
    return render(request, 'dashboard/_client_summary.html', {
        'client_summary': services.get_client_summary(request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_homeworker_summary(request):
    return render(request, 'dashboard/_homeworker_summary.html', {
        'homeworker_summary': services.get_homeworker_summary(request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_domain_hosting(request):
    return render(request, 'dashboard/_domain_hosting_panel.html', {
        'domain_hosting_panel': services.get_domain_hosting_panel(request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_my_tasks(request):
    return render(request, 'dashboard/_my_tasks.html', {
        'my_tasks': services.get_my_tasks(request.user),
    })


@login_required
@require_http_methods(['GET'])
def dashboard_comments(request):
    return render(request, 'dashboard/_recent_comments.html', {
        'recent_comments': services.get_recent_comments(request.user),
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
    return JsonResponse(services.get_monthly_ticket_trend(request.user))


@login_required
@require_http_methods(['GET'])
def chart_tickets_by_status(request):
    return JsonResponse(services.get_tickets_by_status(request.user))


@login_required
@require_http_methods(['GET'])
def chart_client_wise_tickets(request):
    return JsonResponse(services.get_client_wise_tickets(request.user))


@login_required
@require_http_methods(['GET'])
def chart_staff_productivity(request):
    return JsonResponse(services.get_staff_productivity(request.user))


@login_required
@require_http_methods(['GET'])
def chart_asset_status(request):
    return JsonResponse(services.get_asset_status_distribution(request.user))


@login_required
@require_http_methods(['GET'])
def chart_device_categories(request):
    return JsonResponse(services.get_device_category_distribution(request.user))


@login_required
@require_http_methods(['GET'])
def chart_domain_hosting(request):
    return JsonResponse(services.get_domain_hosting_overview(request.user))


@login_required
@require_http_methods(['GET'])
def chart_client_state(request):
    return JsonResponse(services.get_client_state_distribution(request.user))
