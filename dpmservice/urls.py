from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('masters/', include('masters.urls', namespace='masters')),
    path('company/', include('clients.urls', namespace='clients')),
    path('inventory/', include('assets.urls', namespace='assets')),
    path('', include('tickets.urls', namespace='tickets')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('hosting/', include('hosting.urls', namespace='hosting')),
    path('comments/', include('comments.urls', namespace='comments')),
    path('api/', include('api.urls', namespace='api')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('authorization/', include('authorization.urls', namespace='authorization')),
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
