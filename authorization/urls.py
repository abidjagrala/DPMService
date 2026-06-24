from django.urls import path

from . import views

app_name = 'authorization'

urlpatterns = [
    path('', views.auth_dashboard, name='auth_dashboard'),

    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),

    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:pk>/', views.role_detail, name='role_detail'),
    path('roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    path('roles/<int:pk>/clone/', views.role_clone, name='role_clone'),

    path('permissions/modules/', views.module_permission_matrix, name='module_perm_matrix'),
    path('permissions/modules/save/', views.module_permission_save, name='module_perm_save'),

    path('permissions/models/', views.model_permission_matrix, name='model_perm_matrix'),
    path('permissions/models/save/', views.model_permission_save, name='model_perm_save'),

    path('permissions/fields/', views.field_permission_matrix, name='field_perm_matrix'),
    path('permissions/fields/save/', views.field_permission_save, name='field_perm_save'),

    path('permissions/menus/', views.menu_permission_matrix, name='menu_perm_matrix'),
    path('permissions/menus/save/', views.menu_permission_save, name='menu_perm_save'),

    path('assignments/', views.user_assignment_list, name='user_assignment_list'),
    path('assignments/create/', views.user_assignment_create, name='user_assignment_create'),
    path('assignments/<int:pk>/edit/', views.user_assignment_edit, name='user_assignment_edit'),
    path('assignments/<int:pk>/delete/', views.user_assignment_delete, name='user_assignment_delete'),

    path('audit-log/', views.audit_log_list, name='audit_log_list'),

    path('seed/', views.seed_defaults, name='seed_defaults'),
]
