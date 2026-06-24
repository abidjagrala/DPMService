from django.urls import path

from . import views

app_name = 'hosting'

urlpatterns = [
    path('', views.hosting_list_view, name='hosting_list'),
    path('export/', views.hosting_export_csv, name='hosting_export_csv'),
    path('template/', views.hosting_download_template, name='hosting_download_template'),
    path('import/', views.hosting_import_csv, name='hosting_import'),
    path('new/', views.hosting_create_view, name='hosting_create'),
    path('<int:pk>/', views.hosting_detail_view, name='hosting_detail'),
    path('<int:pk>/edit/', views.hosting_update_view, name='hosting_update'),
    path('<int:pk>/delete/', views.hosting_delete_view, name='hosting_delete'),
    path('<int:service_pk>/invoices/new/', views.hosting_invoice_create_view, name='invoice_create'),
    path('<int:service_pk>/invoices/<int:pk>/delete/', views.hosting_invoice_delete_view, name='invoice_delete'),
]
