from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list_view, name='notification_list'),
    path('unread-count/', views.notification_unread_count_view, name='unread_count'),
    path('<int:pk>/read/', views.notification_mark_read_view, name='mark_read'),
    path('read-all/', views.notification_mark_all_read_view, name='mark_all_read'),
]
