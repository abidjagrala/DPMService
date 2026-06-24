from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HostingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hosting'
    verbose_name = _('Domain and Hosting Services')
