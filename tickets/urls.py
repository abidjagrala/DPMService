from django.urls import path

from . import views

app_name = 'tickets'

urlpatterns = [
    path('tickets/', views.ticket_list_view, name='ticket_list'),
    path('tickets/new/', views.ticket_create_view, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail_view, name='ticket_detail'),
    path('tickets/<int:pk>/edit/', views.ticket_update_view, name='ticket_update'),
    path('tickets/<int:pk>/delete/', views.ticket_delete_view, name='ticket_delete'),
    path('tickets/<int:pk>/status/', views.ticket_status_view, name='ticket_status'),
    path('tracking/<str:ticket_number>/', views.public_tracking_view, name='public_tracking'),
]
