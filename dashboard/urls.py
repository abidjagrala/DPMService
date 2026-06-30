from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),

    # HTMX partials
    path('htmx/kpis/', views.dashboard_kpis, name='htmx_kpis'),
    path('htmx/charts/', views.dashboard_charts, name='htmx_charts'),
    path('htmx/recent-tickets/', views.dashboard_recent_tickets, name='htmx_recent_tickets'),
    path('htmx/activities/', views.dashboard_activities, name='htmx_activities'),
    path('htmx/expiry-alerts/', views.dashboard_expiry_alerts, name='htmx_expiry_alerts'),
    path('htmx/client-summary/', views.dashboard_client_summary, name='htmx_client_summary'),
    path('htmx/homeworker-summary/', views.dashboard_homeworker_summary, name='htmx_homeworker_summary'),
    path('htmx/domain-hosting/', views.dashboard_domain_hosting, name='htmx_domain_hosting'),
    path('htmx/my-tasks/', views.dashboard_my_tasks, name='htmx_my_tasks'),
    path('htmx/comments/', views.dashboard_comments, name='htmx_comments'),
    path('htmx/quick-actions/', views.dashboard_quick_actions, name='htmx_quick_actions'),

    # Chart JSON APIs
    path('api/monthly-trend/', views.chart_monthly_trend, name='chart_monthly_trend'),
    path('api/tickets-by-status/', views.chart_tickets_by_status, name='chart_tickets_by_status'),
    path('api/client-wise-tickets/', views.chart_client_wise_tickets, name='chart_client_wise_tickets'),
    path('api/staff-productivity/', views.chart_staff_productivity, name='chart_staff_productivity'),
    path('api/asset-status/', views.chart_asset_status, name='chart_asset_status'),
    path('api/domain-hosting/', views.chart_domain_hosting, name='chart_domain_hosting'),
    path('api/client-state/', views.chart_client_state, name='chart_client_state'),
]
