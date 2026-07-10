from django.urls import path

from . import views

app_name = 'system'

urlpatterns = [
    path('backup/', views.backup_view, name='backup'),
    path('restore/', views.restore_view, name='backup_restore'),
]
