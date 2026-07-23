from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('heartbeat/', views.heartbeat_view, name='heartbeat'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/password/', views.password_change_view, name='password_change'),
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/<uuid:token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password-reset/success/', views.password_reset_success_view, name='password_reset_success'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/new/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_update_view, name='user_update'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    path('users/<int:user_id>/2fa-toggle/', views.user_2fa_toggle_view, name='user_2fa_toggle'),
    path('company-info/', views.company_info_edit_view, name='company_info_edit'),
    path('mail-settings/', views.mail_settings_edit_view, name='mail_settings_edit'),
    path('mail-settings/test/', views.mail_settings_test_view, name='mail_settings_test'),
    path('sms-settings/', views.sms_settings_edit_view, name='sms_settings_edit'),
    path('sms-settings/test/', views.sms_settings_test_view, name='sms_settings_test'),
    path('whatsapp-settings/', views.whatsapp_settings_edit_view, name='whatsapp_settings_edit'),
    path('whatsapp-settings/test/', views.whatsapp_settings_test_view, name='whatsapp_settings_test'),
    path('totp/setup/', views.totp_setup_view, name='totp_setup'),
    path('totp/verify/', views.totp_verify_view, name='totp_verify'),
    path('totp/disable/', views.totp_disable_view, name='totp_disable'),
    path('totp/enable/', views.totp_enable_view, name='totp_enable'),
    path('totp/setup/enable/', views.totp_setup_enable_view, name='totp_setup_enable'),
]
