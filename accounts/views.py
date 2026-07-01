import json

from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .captcha import validate_captcha, store_captcha_answer
from .forms import AdminUserForm, EmailLoginForm, ProfileUpdateForm
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
                return HttpResponseForbidden('You do not have permission to access this page.')
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

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        ip = _get_client_ip(request)

        if is_locked_out(email, ip):
            messages.error(request, 'Too many failed login attempts. Please try again in 5 minutes.')
            form = EmailLoginForm(request)
            return render(request, 'accounts/login.html', {'form': form})

        captcha_value = request.POST.get('captcha', '')
        if not validate_captcha(request, captcha_value):
            messages.error(request, 'Invalid captcha answer. Please try again.')
            form = EmailLoginForm(request)
            return render(request, 'accounts/login.html', {'form': form})

        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            reset_attempts(email, ip)
            store_captcha_answer(request, None)
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_short_name()}.')
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url or 'accounts:dashboard')
        else:
            record_failed_attempt(email, ip)
            remaining = get_remaining_attempts(email, ip)
            if remaining > 0:
                messages.warning(request, f'Invalid credentials. {remaining} attempts remaining before lockout.')
    else:
        form = EmailLoginForm(request)

    from .captcha import MathCaptchaWidget
    widget = MathCaptchaWidget()
    store_captcha_answer(request, widget.answer)
    captcha_html = widget.render('captcha', '', {})

    return render(request, 'accounts/login.html', {
        'form': form,
        'captcha_html': captcha_html,
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

    template = 'accounts/_user_form_partial.html' if is_htmx(request) else 'accounts/user_form.html'
    return render(request, template, {
        'form': form,
        'mode': 'create',
    })


@role_required(User.Role.ADMIN)
@csrf_protect
@require_http_methods(['GET', 'POST'])
def user_update_view(request, user_id):
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

    template = 'accounts/_user_form_partial.html' if is_htmx(request) else 'accounts/user_form.html'
    return render(request, template, {
        'form': form,
        'mode': 'update',
        'user_obj': target_user,
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
