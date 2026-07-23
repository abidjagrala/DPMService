from django.urls import path

from . import views

app_name = 'clients'

urlpatterns = [
    # Branch
    path('branches/', views.branch_list_view, name='branch_list'),
    path('branches/new/', views.branch_create_view, name='branch_create'),
    path('branches/<int:pk>/edit/', views.branch_update_view, name='branch_update'),
    path('branches/<int:pk>/delete/', views.branch_delete_view, name='branch_delete'),
    path('api/branches/', views.branch_api_view, name='branch_api'),

    # Client
    path('clients/', views.client_list_view, name='client_list'),
    path('clients/export/', views.client_export_csv, name='client_export_csv'),
    path('clients/template/', views.client_download_template, name='client_download_template'),
    path('clients/import/', views.client_import_csv, name='client_import'),
    path('clients/city-select/', views.client_city_select_partial, name='client_city_select'),
    path('clients/new/', views.client_create_view, name='client_create'),
    path('clients/<int:pk>/', views.client_detail_view, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_update_view, name='client_update'),
    path('clients/<int:pk>/delete/', views.client_delete_view, name='client_delete'),

    # Employee
    path('employees/', views.employee_list_view, name='employee_list'),
    path('employees/export/', views.employee_export_csv, name='employee_export_csv'),
    path('employees/new/', views.employee_create_view, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail_view, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_update_view, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete_view, name='employee_delete'),

    # Location
    path('locations/', views.location_list_view, name='location_list'),
    path('locations/new/', views.location_create_view, name='location_create'),
    path('locations/<int:pk>/edit/', views.location_update_view, name='location_update'),
    path('locations/<int:pk>/delete/', views.location_delete_view, name='location_delete'),

    # Quick-Create (inline add from other forms)
    path('quick-new/branch/', views.branch_quick_create_view, name='branch_quick_create'),
    path('quick-new/client/', views.client_quick_create_view, name='client_quick_create'),
    path('quick-new/location/', views.location_quick_create_view, name='location_quick_create'),
]
