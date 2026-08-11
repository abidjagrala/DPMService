import json

from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .captcha import validate_captcha, store_captcha_answer
from .forms import AdminUserForm, EmailLoginForm, PasswordResetConfirmForm, PasswordResetRequestForm, ProfileUpdateForm
from .services.login_throttle import (
    get_remaining_attempts,
    is_locked_out,
    record_failed_attempt,
    reset_attempts,
)

User = get_user_model()


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles and not request.user.is_superuser:
                from django.shortcuts import render as _render
                return _render(request, 'accounts/403.html', status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def hx_toast(level, message, status=200, extra_events=None):
    payload = {
        'toast': {'level': level, 'message': str(message)},
    }
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


def hx_redirect(url, level=None, message=None):
    response = HttpResponse(status=200)
    response['HX-Redirect'] = url
    if level and message:
        response['HX-Trigger'] = json.dumps({'toast': {'level': level, 'message': str(message)}})
    return response


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


@csrf_protect
@never_cache
@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    from .captcha import MathCaptchaWidget

    def _new_captcha():
        widget = MathCaptchaWidget()
        store_captcha_answer(request, widget.answer)
        return widget.render('captcha', '', {})

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        ip = _get_client_ip(request)

        if is_locked_out(email, ip):
            messages.error(request, 'Too many failed login attempts. Please try again in 5 minutes.')
            form = EmailLoginForm(request)
            return render(request, 'accounts/login.html', {'form': form, 'captcha_html': _new_captcha()})

        captcha_value = request.POST.get('captcha', '')
        if not validate_captcha(request, captcha_value):
            messages.error(request, 'Invalid captcha answer. Please try again.')
            form = EmailLoginForm(request)
            return render(request, 'accounts/login.html', {'form': form, 'captcha_html': _new_captcha()})

        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            reset_attempts(email, ip)
            if user.two_factor_enabled and user.totp_secret:
                request.session['pre_2fa_user_id'] = user.pk
                return redirect('accounts:totp_verify')
            elif not user.two_factor_enabled and not user.totp_secret:
                login(request, user)
                return redirect('accounts:dashboard')
            else:
                request.session['pre_2fa_user_id'] = user.pk
                return redirect('accounts:totp_setup')
        else:
            record_failed_attempt(email, ip)
            remaining = get_remaining_attempts(email, ip)
            if remaining > 0:
                messages.warning(request, f'Invalid credentials. {remaining} attempts remaining before lockout.')
    else:
        form = EmailLoginForm(request)

    return render(request, 'accounts/login.html', {
        'form': form,
        'captcha_html': _new_captcha(),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
@require_http_methods(['GET'])
def heartbeat_view(request):
    from django.http import JsonResponse
    from django.utils import timezone as tz
    request.session['last_activity'] = tz.now().isoformat()
    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(['GET'])
def dashboard_view(request):
    from django.shortcuts import redirect as _redirect
    return _redirect('dashboard:dashboard')


@login_required
@require_http_methods(['GET'])
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user_obj': request.user})


@login_required
@csrf_protect
@require_http_methods(['GET', 'POST'])
def profile_edit_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
@csrf_protect
@require_http_methods(['GET', 'POST'])
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'accounts/password_change.html', {'form': form})


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_http_methods(['GET'])
def user_list_view(request):
    from django.db.models import Q

    users = User.objects.all()
    search = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '')

    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    if role_filter in dict(User.Role.choices):
        users = users.filter(role=role_filter)

    context = {
        'users': users,
        'roles': User.Role.choices,
        'search': search,
        'selected_role': role_filter,
    }
    if is_htmx(request):
        return render(request, 'accounts/_user_list_table.html', context)
    return render(request, 'accounts/user_list.html', context)


@role_required(User.Role.ADMIN)
@require_http_methods(['GET'])
def user_detail_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    return render(request, 'accounts/user_detail.html', {'user_obj': target_user})


@role_required(User.Role.ADMIN)
@csrf_protect
@require_http_methods(['GET', 'POST'])
def user_create_view(request):
    from clients.models import Client
    if request.method == 'POST':
        form = AdminUserForm(request.POST, is_create=True)
        if form.is_valid():
            user = form.save()
            if is_htmx(request):
                return hx_toast('success', f'User {user.email} created.', status=204, extra_events={'user-saved': True})
            messages.success(request, f'User {user.email} created successfully.')
            return redirect('accounts:user_detail', user_id=user.pk)
    else:
        form = AdminUserForm(is_create=True)

    available_clients = Client.objects.filter(is_active=True).order_by('company_name')
    template = 'accounts/_user_form_partial.html' if is_htmx(request) else 'accounts/user_form.html'
    return render(request, template, {
        'form': form,
        'mode': 'create',
        'available_clients': available_clients,
    })


@role_required(User.Role.ADMIN)
@csrf_protect
@require_http_methods(['GET', 'POST'])
def user_update_view(request, user_id):
    from clients.models import Client
    target_user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=target_user, is_create=False)
        if form.is_valid():
            if target_user.pk == request.user.pk:
                if form.cleaned_data.get('is_active') is False:
                    form.add_error('is_active', _('You cannot deactivate your own account.'))
                if target_user.is_superuser and not form.cleaned_data.get('is_staff'):
                    form.add_error('is_staff', _('You cannot remove your own staff status.'))
            if not form.errors:
                user = form.save()
                if is_htmx(request):
                    return hx_toast('success', f'User {user.email} updated.', status=204, extra_events={'user-saved': True})
                messages.success(request, f'User {user.email} updated successfully.')
                return redirect('accounts:user_detail', user_id=user.pk)
    else:
        form = AdminUserForm(instance=target_user, is_create=False)

    available_clients = Client.objects.filter(is_active=True).order_by('company_name')
    template = 'accounts/_user_form_partial.html' if is_htmx(request) else 'accounts/user_form.html'
    return render(request, template, {
        'form': form,
        'mode': 'update',
        'user_obj': target_user,
        'available_clients': available_clients,
    })


@role_required(User.Role.ADMIN)
@csrf_protect
@require_http_methods(['GET', 'POST'])
def user_delete_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)

    if target_user.pk == request.user.pk:
        if is_htmx(request):
            return hx_toast('error', 'You cannot delete your own account.', status=200)
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:user_detail', user_id=target_user.pk)

    if request.method == 'POST':
        email = target_user.email
        target_user.delete()
        if is_htmx(request):
            return hx_toast('success', f'User {email} deleted.', status=204, extra_events={'user-saved': True})
        messages.success(request, f'User {email} deleted successfully.')
        return redirect('accounts:user_list')

    template = 'accounts/_user_confirm_delete_partial.html' if is_htmx(request) else 'accounts/user_confirm_delete.html'
    return render(request, template, {'user_obj': target_user})


@role_required(User.Role.ADMIN)
@csrf_protect
@require_http_methods(['POST'])
def user_2fa_toggle_view(request, user_id):
    """Admin toggle 2FA for a user (force enable/disable without TOTP verification)."""
    target_user = get_object_or_404(User, pk=user_id)

    action = request.POST.get('action', '')

    if action == 'disable':
        target_user.totp_secret = ''
        target_user.two_factor_enabled = False
        target_user.save(update_fields=['totp_secret', 'two_factor_enabled'])
        messages.success(request, f'2FA disabled for {target_user.email}.')
    elif action == 'enable':
        target_user.two_factor_enabled = False
        target_user.totp_secret = ''
        target_user.save(update_fields=['two_factor_enabled', 'totp_secret'])
        messages.success(request, f'2FA enabled for {target_user.email}. User must complete 2FA setup on next login.')
    else:
        messages.error(request, 'Invalid action.')

    return redirect('accounts:user_detail', user_id=target_user.pk)


@csrf_protect
@never_cache
@require_http_methods(['GET', 'POST'])
def password_reset_request_view(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email__iexact=email, is_active=True)
                token = user.generate_password_reset_token()
                _send_password_reset_email(request, user, token)
            except User.DoesNotExist:
                pass
            messages.success(request, 'If an account exists with this email, a password reset link has been sent.')
            return redirect('accounts:login')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'accounts/password_reset_request.html', {'form': form})


@csrf_protect
@never_cache
@require_http_methods(['GET', 'POST'])
def password_reset_confirm_view(request, token):
    try:
        user = User.objects.get(password_reset_token=token, is_active=True)
    except User.DoesNotExist:
        messages.error(request, 'Invalid or expired password reset link.')
        return redirect('accounts:password_reset_request')

    if not user.is_password_reset_token_valid():
        user.clear_password_reset_token()
        messages.error(request, 'Password reset link has expired. Please request a new one.')
        return redirect('accounts:password_reset_request')

    if request.method == 'POST':
        form = PasswordResetConfirmForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your password has been reset successfully. You can now sign in.')
            return redirect('accounts:login')
    else:
        form = PasswordResetConfirmForm(user=user)

    return render(request, 'accounts/password_reset_confirm.html', {'form': form, 'token': token})


def password_reset_success_view(request):
    return render(request, 'accounts/password_reset_success.html')


def _send_password_reset_email(request, user, token):
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse

    from accounts.models import MailSettings
    mail_config = MailSettings.get_instance()
    if not mail_config.is_active:
        return
    mail_config.apply_to_settings()

    reset_url = request.build_absolute_uri(
        reverse('accounts:password_reset_confirm', kwargs={'token': str(token)})
    )
    subject = 'Password Reset Request - DPM Service'
    message = (
        f'Hello {user.get_full_name()},\n\n'
        f'You have requested to reset your password. Please click the link below to set a new password:\n\n'
        f'{reset_url}\n\n'
        f'This link will expire in 1 hour.\n\n'
        f'If you did not request this, please ignore this email.\n\n'
        f'Regards,\n'
        f'DPM Service Team'
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error('Password reset email failed to %s: %s', user.email, e)


# ---------------------------------------------------------------------------
# Company Info (singleton)
# ---------------------------------------------------------------------------

@role_required('admin')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def company_info_edit_view(request):
    from .forms import CompanyInfoForm
    from .models import CompanyInfo

    company = CompanyInfo.get_instance()

    if request.method == 'POST':
        form = CompanyInfoForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, _('Company information updated successfully.'))
            return redirect('accounts:company_info_edit')
    else:
        form = CompanyInfoForm(instance=company)

    return render(request, 'accounts/company_info_edit.html', {
        'form': form,
        'obj': company,
        'page_title': _('Company Information'),
    })


# ---------------------------------------------------------------------------
# Mail Settings (singleton)
# ---------------------------------------------------------------------------

@role_required('admin')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def mail_settings_edit_view(request):
    from .forms import MailSettingsForm
    from .models import MailSettings

    mail_config = MailSettings.get_instance()

    if request.method == 'POST':
        form = MailSettingsForm(request.POST, instance=mail_config)
        if form.is_valid():
            mail_settings_obj = form.save()
            mail_settings_obj.apply_to_settings()
            messages.success(request, _('Mail settings updated successfully.'))
            return redirect('accounts:mail_settings_edit')
    else:
        form = MailSettingsForm(instance=mail_config)

    return render(request, 'accounts/mail_settings_edit.html', {
        'form': form,
        'obj': mail_config,
        'page_title': _('Mail Settings'),
    })


@role_required('admin')
@csrf_protect
@require_http_methods(['POST'])
def mail_settings_test_view(request):
    """Send a test email using the current mail settings."""
    from django.core.mail import send_mail
    from django.conf import settings
    from .models import MailSettings

    mail_config = MailSettings.get_instance()
    if not mail_config.is_active:
        return JsonResponse({'success': False, 'error': _('Email sending is disabled. Enable it first.')})
    if not mail_config.from_email and not settings.DEFAULT_FROM_EMAIL:
        return JsonResponse({'success': False, 'error': _('Please set a "From Email" address first.')})

    mail_config.apply_to_settings()

    test_email = request.POST.get('email', '').strip()
    if not test_email:
        return JsonResponse({'success': False, 'error': _('Please enter an email address.')})

    try:
        send_mail(
            subject='DPM Service — Test Email',
            message=(
                'This is a test email from DPM Service.\n\n'
                'If you received this, your mail settings are working correctly.\n\n'
                f'SMTP Host: {mail_config.host}\n'
                f'Port: {mail_config.port}\n'
                f'Security: {mail_config.get_security_display()}\n'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ---------------------------------------------------------------------------
# SMS Settings (singleton)
# ---------------------------------------------------------------------------

@role_required('admin')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def sms_settings_edit_view(request):
    from .forms import SmsSettingsForm
    from .models import SmsSettings

    sms_config = SmsSettings.get_instance()

    if request.method == 'POST':
        form = SmsSettingsForm(request.POST, instance=sms_config)
        if form.is_valid():
            form.save()
            messages.success(request, _('SMS settings updated successfully.'))
            return redirect('accounts:sms_settings_edit')
    else:
        form = SmsSettingsForm(instance=sms_config)

    return render(request, 'accounts/sms_settings_edit.html', {
        'form': form,
        'obj': sms_config,
        'page_title': _('SMS Settings'),
    })


@role_required('admin')
@csrf_protect
@require_http_methods(['POST'])
def sms_settings_test_view(request):
    """Send a test SMS using the current MSG91 settings."""
    import json as json_mod
    from .models import SmsSettings

    sms_config = SmsSettings.get_instance()
    if not sms_config.is_active:
        return JsonResponse({'success': False, 'error': _('SMS sending is disabled. Enable it first.')})
    if not sms_config.auth_key:
        return JsonResponse({'success': False, 'error': _('Please set an auth key first.')})

    test_phone = request.POST.get('phone', '').strip()
    if not test_phone:
        return JsonResponse({'success': False, 'error': _('Please enter a phone number.')})

    try:
        import urllib.request
        payload = json_mod.dumps({
            'sender': sms_config.sender_id,
            'route': str(sms_config.route),
            'country': str(sms_config.country),
            'sms': [{
                'message': 'DPM Service — Test SMS. If you received this, your SMS settings are working correctly.',
                'to': [test_phone],
            }],
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.msg91.com/api/v2/sendsms',
            data=payload,
            headers={
                'authkey': sms_config.auth_key,
                'Content-Type': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json_mod.loads(resp.read().decode('utf-8'))

        if result.get('type') == 'success':
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': result.get('message', 'Unknown error from MSG91')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ---------------------------------------------------------------------------
# WhatsApp Settings (singleton)
# ---------------------------------------------------------------------------

@role_required('admin')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def whatsapp_settings_edit_view(request):
    from .forms import WhatsappSettingsForm
    from .models import WhatsappSettings

    wa_config = WhatsappSettings.get_instance()

    if request.method == 'POST':
        form = WhatsappSettingsForm(request.POST, instance=wa_config)
        if form.is_valid():
            form.save()
            messages.success(request, _('WhatsApp settings updated successfully.'))
            return redirect('accounts:whatsapp_settings_edit')
    else:
        form = WhatsappSettingsForm(instance=wa_config)

    return render(request, 'accounts/whatsapp_settings_edit.html', {
        'form': form,
        'obj': wa_config,
        'page_title': _('WhatsApp Settings'),
    })


@role_required('admin')
@csrf_protect
@require_http_methods(['POST'])
def whatsapp_settings_test_view(request):
    """Send a test WhatsApp template message using the current MSG91 settings."""
    import json as json_mod
    from .models import WhatsappSettings

    wa_config = WhatsappSettings.get_instance()
    if not wa_config.is_active:
        return JsonResponse({'success': False, 'error': _('WhatsApp sending is disabled. Enable it first.')})
    if not wa_config.auth_key:
        return JsonResponse({'success': False, 'error': _('Please set an auth key first.')})
    if not wa_config.template_id:
        return JsonResponse({'success': False, 'error': _('Please set a template ID first.')})
    if not wa_config.whatsapp_number:
        return JsonResponse({'success': False, 'error': _('Please set your WhatsApp business number first.')})

    test_phone = request.POST.get('phone', '').strip()
    if not test_phone:
        return JsonResponse({'success': False, 'error': _('Please enter a phone number.')})

    try:
        import urllib.request
        payload = json_mod.dumps({
            'sender': wa_config.whatsapp_number,
            'number': test_phone,
            'template_id': wa_config.template_id,
            'variables': ['DPM Service'],
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.msg91.com/api/v5/whatsapp/send/template',
            data=payload,
            headers={
                'authkey': wa_config.auth_key,
                'Content-Type': 'application/json',
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json_mod.loads(resp.read().decode('utf-8'))

        if result.get('type') == 'success':
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': result.get('message', 'Unknown error from MSG91')})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ---------------------------------------------------------------------------
# Two-Factor Authentication (TOTP)
# ---------------------------------------------------------------------------

import io
import base64

import pyotp
import qrcode


def _get_pre_2fa_user(request):
    """Retrieve the user awaiting 2FA verification from the session."""
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


@csrf_protect
@never_cache
@require_http_methods(['GET', 'POST'])
def totp_setup_view(request):
    """First-time TOTP setup: show QR code, validate first code, enable 2FA."""
    user = _get_pre_2fa_user(request)
    if not user:
        messages.error(request, _('Session expired. Please log in again.'))
        return redirect('accounts:login')

    # If user already has 2FA enabled, redirect to verify
    if user.totp_secret:
        return redirect('accounts:totp_verify')

    if request.method == 'GET':
        secret = pyotp.random_base32()
        request.session['totp_setup_secret'] = secret
    else:
        secret = request.session.get('totp_setup_secret')
        if not secret:
            return redirect('accounts:totp_setup')

    totp = pyotp.TOTP(secret)
    issuer = 'DPM Service'
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=issuer)

    # Generate QR code as base64 PNG
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    error = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not code or len(code) != 6 or not code.isdigit():
            error = _('Please enter a valid 6-digit code.')
        else:
            verify_totp = pyotp.TOTP(secret)
            if verify_totp.verify(code, valid_window=2):
                user.totp_secret = secret
                user.two_factor_enabled = True
                user.save(update_fields=['totp_secret', 'two_factor_enabled'])
                request.session.pop('totp_setup_secret', None)
                login(request, user)
                request.session.pop('pre_2fa_user_id', None)
                messages.success(request, _('Two-factor authentication has been enabled.'))
                return redirect('accounts:dashboard')
            else:
                error = _('Invalid code. Please try again.')

    return render(request, 'accounts/totp_setup.html', {
        'qr_b64': qr_b64,
        'secret': secret,
        'error': error,
    })


@csrf_protect
@never_cache
@require_http_methods(['GET', 'POST'])
def totp_verify_view(request):
    """Verify TOTP code on subsequent logins."""
    user = _get_pre_2fa_user(request)
    if not user:
        messages.error(request, _('Session expired. Please log in again.'))
        return redirect('accounts:login')

    if not user.totp_secret:
        return redirect('accounts:totp_setup')

    error = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not code or len(code) != 6 or not code.isdigit():
            error = _('Please enter a valid 6-digit code.')
        else:
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(code, valid_window=2):
                login(request, user)
                request.session.pop('pre_2fa_user_id', None)
                messages.success(request, _('Welcome back, ') + user.get_short_name() + '.')
                next_url = request.session.pop('next_url', None)
                return redirect(next_url or 'accounts:dashboard')
            else:
                error = _('Invalid code. Please try again.')

    return render(request, 'accounts/totp_verify.html', {
        'error': error,
    })


@login_required
@csrf_protect
@require_http_methods(['GET', 'POST'])
def totp_disable_view(request):
    """Disable 2FA after verifying current TOTP code."""
    user = request.user

    if not user.two_factor_enabled or not user.totp_secret:
        messages.info(request, _('Two-factor authentication is not enabled.'))
        return redirect('accounts:profile')

    error = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not code or len(code) != 6 or not code.isdigit():
            error = _('Please enter a valid 6-digit code.')
        else:
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(code, valid_window=2):
                user.totp_secret = ''
                user.two_factor_enabled = False
                user.save(update_fields=['totp_secret', 'two_factor_enabled'])
                messages.success(request, _('Two-factor authentication has been disabled.'))
                return redirect('accounts:profile')
            else:
                error = _('Invalid code. Please try again.')

    return render(request, 'accounts/totp_disable.html', {
        'error': error,
    })


@login_required
@csrf_protect
@require_http_methods(['POST'])
def totp_enable_view(request):
    """Redirect to TOTP setup to enable 2FA."""
    user = request.user

    if user.two_factor_enabled and user.totp_secret:
        messages.info(request, _('Two-factor authentication is already enabled.'))
        return redirect('accounts:profile')

    return redirect('accounts:totp_setup_enable')


@login_required
@csrf_protect
@never_cache
@require_http_methods(['GET', 'POST'])
def totp_setup_enable_view(request):
    """TOTP setup for enabling 2FA from profile (authenticated user)."""
    user = request.user

    if user.two_factor_enabled and user.totp_secret:
        return redirect('accounts:profile')

    if request.method == 'GET':
        secret = pyotp.random_base32()
        request.session['totp_setup_secret'] = secret
    else:
        secret = request.session.get('totp_setup_secret')
        if not secret:
            return redirect('accounts:totp_setup_enable')

    totp = pyotp.TOTP(secret)
    issuer = 'DPM Service'
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name=issuer)

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    error = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not code or len(code) != 6 or not code.isdigit():
            error = _('Please enter a valid 6-digit code.')
        else:
            verify_totp = pyotp.TOTP(secret)
            if verify_totp.verify(code, valid_window=2):
                user.totp_secret = secret
                user.two_factor_enabled = True
                user.save(update_fields=['totp_secret', 'two_factor_enabled'])
                request.session.pop('totp_setup_secret', None)
                messages.success(request, _('Two-factor authentication has been enabled.'))
                return redirect('accounts:profile')
            else:
                error = _('Invalid code. Please try again.')

    return render(request, 'accounts/totp_setup.html', {
        'qr_b64': qr_b64,
        'secret': secret,
        'error': error,
    })
