from django.urls import path

from . import views

app_name = 'masters'

urlpatterns = [
    # State
    path('states/', views.state_list_view, name='state_list'),
    path('states/new/', views.state_create_view, name='state_create'),
    path('states/<int:pk>/edit/', views.state_update_view, name='state_update'),
    path('states/<int:pk>/delete/', views.state_delete_view, name='state_delete'),

    # City
    path('cities/', views.city_list_view, name='city_list'),
    path('cities/new/', views.city_create_view, name='city_create'),
    path('cities/<int:pk>/edit/', views.city_update_view, name='city_update'),
    path('cities/<int:pk>/delete/', views.city_delete_view, name='city_delete'),

    # Service Type
    path('service-types/', views.service_type_list_view, name='service_type_list'),
    path('service-types/new/', views.service_type_create_view, name='service_type_create'),
    path('service-types/<int:pk>/edit/', views.service_type_update_view, name='service_type_update'),
    path('service-types/<int:pk>/delete/', views.service_type_delete_view, name='service_type_delete'),

    # Asset Type
    path('asset-types/', views.asset_type_list_view, name='asset_type_list'),
    path('asset-types/new/', views.asset_type_create_view, name='asset_type_create'),
    path('asset-types/<int:pk>/edit/', views.asset_type_update_view, name='asset_type_update'),
    path('asset-types/<int:pk>/delete/', views.asset_type_delete_view, name='asset_type_delete'),

    # Transport Type
    path('transport-types/', views.transport_type_list_view, name='transport_type_list'),
    path('transport-types/new/', views.transport_type_create_view, name='transport_type_create'),
    path('transport-types/<int:pk>/edit/', views.transport_type_update_view, name='transport_type_update'),
    path('transport-types/<int:pk>/delete/', views.transport_type_delete_view, name='transport_type_delete'),
]
