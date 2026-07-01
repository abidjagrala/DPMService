from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


class IdleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            now = timezone.now()

            if last_activity:
                try:
                    last_activity_dt = timezone.datetime.fromisoformat(last_activity)
                    if last_activity_dt.tzinfo is None:
                        last_activity_dt = timezone.make_aware(last_activity_dt)
                    idle_time = now - last_activity_dt
                    if idle_time > timedelta(seconds=settings.SESSION_COOKIE_AGE):
                        logout(request)
                        messages.info(request, 'You have been logged out due to inactivity.')
                        return redirect(settings.LOGIN_URL)
                except (ValueError, TypeError):
                    pass

            request.session['last_activity'] = now.isoformat()

        response = self.get_response(request)
        return response
