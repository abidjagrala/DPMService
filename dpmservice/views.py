import logging
import traceback

from django.http import HttpResponseServerError
from django.shortcuts import render

logger = logging.getLogger(__name__)

ERROR_PAGE_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{code} — {title}</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8fafc;color:#1e293b}
.box{text-align:center;padding:3rem}
.code{font-size:6rem;font-weight:900;opacity:.15;line-height:1}
h1{font-size:1.5rem;margin:1rem 0 .5rem}
p{color:#64748b;max-width:28rem;margin:0 auto 1.5rem}
.btn{display:inline-block;padding:.5rem 1.5rem;border-radius:.5rem;text-decoration:none;
font-weight:500;margin:0 .25rem}
.primary{background:#3b82f6;color:#fff}
.ghost{background:#e2e8f0;color:#475569}
</style>
</head>
<body>
<div class="box">
<div class="code">{code}</div>
<h1>{title}</h1>
<p>{message}</p>
<a href="/" class="btn primary">Go to Home</a>
<button onclick="history.back()" class="btn ghost">Go Back</button>
</div>
</body>
</html>"""


def _safe_render(request, template, code, title, message, status):
    try:
        return render(request, template, status=status)
    except Exception:
        logger.error('Error template %s failed to render', template)
        html = ERROR_PAGE_HTML.format(code=code, title=title, message=message)
        return HttpResponseServerError(html)


def custom_400(request, exception):
    logger.warning('400 Bad Request: %s', request.path)
    return _safe_render(request, 'accounts/400.html', '400', 'Bad Request',
                        'The server could not understand your request.', 400)


def custom_403(request, exception):
    logger.warning('403 Permission Denied: %s', request.path)
    return _safe_render(request, 'accounts/403.html', '403', 'Permission Denied',
                        'You do not have permission to access this page.', 403)


def custom_404(request, exception):
    logger.warning('404 Not Found: %s', request.path)
    return _safe_render(request, 'accounts/404.html', '404', 'Page Not Found',
                        'The page you are looking for does not exist.', 404)


def custom_500(request):
    logger.error('500 Server Error: %s', request.path, exc_info=True)
    return _safe_render(request, 'accounts/500.html', '500', 'Server Error',
                        'Something went wrong on our end. Please try again later.', 500)
