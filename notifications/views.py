import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx

from .models import Notification


@login_required
@require_http_methods(['GET'])
def notification_list_view(request):
    """List all notifications for the current user."""
    notifications = Notification.objects.filter(recipient=request.user)[:50]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'page_title': 'Notifications',
    }
    if is_htmx(request):
        return render(request, 'notifications/_notification_list_partial.html', context)
    return render(request, 'notifications/notification_list.html', context)


@login_required
@require_http_methods(['GET'])
def notification_unread_count_view(request):
    """Return unread count for the notification bell."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return HttpResponse(str(count), content_type='text/plain')


@login_required
@csrf_protect
@require_http_methods(['POST'])
def notification_mark_read_view(request, pk):
    """Mark a single notification as read."""
    notification = Notification.objects.filter(pk=pk, recipient=request.user).first()
    if notification:
        notification.mark_as_read()

    if is_htmx(request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({'notification-updated': True, 'unread-count': count})
        return response

    return HttpResponse(status=200)


@login_required
@csrf_protect
@require_http_methods(['POST'])
def notification_mark_all_read_view(request):
    """Mark all notifications as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    if is_htmx(request):
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({'notification-updated': True, 'unread-count': 0})
        return response

    return HttpResponse(status=200)
