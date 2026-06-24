from django.urls import path

from . import views

app_name = 'assets'

urlpatterns = [
    path('assets/', views.asset_list_view, name='asset_list'),
    path('assets/export/', views.asset_export_csv, name='asset_export_csv'),
    path('assets/new/', views.asset_create_view, name='asset_create'),
    path('assets/<int:pk>/', views.asset_detail_view, name='asset_detail'),
    path('assets/<int:pk>/pdf/', views.asset_detail_pdf, name='asset_detail_pdf'),
    path('assets/<int:pk>/edit/', views.asset_update_view, name='asset_update'),
    path('assets/<int:pk>/delete/', views.asset_delete_view, name='asset_delete'),
    path('assets/<int:pk>/assign/', views.asset_assign_view, name='asset_assign'),
    path('assets/<int:pk>/return/', views.asset_return_view, name='asset_return'),
    path('assets/<int:pk>/status/', views.asset_status_change_view, name='asset_status_change'),
]
