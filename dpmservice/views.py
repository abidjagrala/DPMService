import logging

from django.shortcuts import render

logger = logging.getLogger(__name__)


def custom_400(request, exception):
    logger.warning('400 Bad Request: %s', request.path)
    return render(request, 'accounts/400.html', status=400)


def custom_403(request, exception):
    logger.warning('403 Permission Denied: %s', request.path)
    return render(request, 'accounts/403.html', status=403)


def custom_404(request, exception):
    logger.warning('404 Not Found: %s', request.path)
    return render(request, 'accounts/404.html', status=404)


def custom_500(request):
    logger.error('500 Server Error: %s', request.path, exc_info=True)
    return render(request, 'accounts/500.html', status=500)
