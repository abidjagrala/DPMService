from django.urls import path

from . import views

app_name = 'clients'

urlpatterns = [
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

    # Homeworker
    path('homeworkers/', views.homeworker_list_view, name='homeworker_list'),
    path('homeworkers/new/', views.homeworker_create_view, name='homeworker_create'),
    path('homeworkers/<int:pk>/', views.homeworker_detail_view, name='homeworker_detail'),
    path('homeworkers/<int:pk>/edit/', views.homeworker_update_view, name='homeworker_update'),
    path('homeworkers/<int:pk>/delete/', views.homeworker_delete_view, name='homeworker_delete'),
]
