from django.urls import path

from . import views

app_name = 'network'

urlpatterns = [
    # Network Devices
    path('devices/', views.device_list_view, name='device_list'),
    path('devices/new/', views.device_create_view, name='device_create'),
    path('devices/multi-new/', views.device_multi_create_view, name='device_multi_create'),
    path('devices/<int:pk>/', views.device_detail_view, name='device_detail'),
    path('devices/<int:pk>/credentials/', views.device_credentials_view, name='device_credentials'),
    path('devices/<int:pk>/edit/', views.device_update_view, name='device_update'),
    path('devices/<int:pk>/delete/', views.device_delete_view, name='device_delete'),
]
