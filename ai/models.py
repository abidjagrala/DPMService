from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AICacheEntry(models.Model):
    """Cached AI responses to avoid duplicate API calls."""

    prompt_hash = models.CharField(
        _('prompt hash'),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_('SHA256 hash of system + user prompt.'),
    )
    response = models.JSONField(_('response'))
    model = models.CharField(_('model'), max_length=50)
    tokens_input = models.PositiveIntegerField(_('input tokens'), default=0)
    tokens_output = models.PositiveIntegerField(_('output tokens'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    expires_at = models.DateTimeField(_('expires at'), db_index=True)

    class Meta:
        verbose_name = _('AI cache entry')
        verbose_name_plural = _('AI cache entries')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.model} — {self.prompt_hash[:12]}…'

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class AIUsageLog(models.Model):
    """Audit log for all AI API calls."""

    feature = models.CharField(
        _('feature'),
        max_length=50,
        help_text=_('e.g. search, classify, suggest, chat'),
    )
    model = models.CharField(_('model'), max_length=50)
    tokens_input = models.PositiveIntegerField(_('input tokens'))
    tokens_output = models.PositiveIntegerField(_('output tokens'))
    cost_estimate = models.DecimalField(
        _('cost estimate (USD)'),
        max_digits=10,
        decimal_places=6,
        default=0,
    )
    response_time_ms = models.PositiveIntegerField(_('response time (ms)'))
    success = models.BooleanField(_('success'), default=True)
    error_message = models.TextField(
        _('error message'),
        blank=True,
        default='',
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('AI usage log')
        verbose_name_plural = _('AI usage logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['feature', 'created_at']),
        ]

    def __str__(self) -> str:
        status = '✓' if self.success else '✗'
        return f'{status} {self.feature} — {self.model} ({self.tokens_input + self.tokens_output} tokens)'


class AISettings(models.Model):
    """Stores AI API provider configuration."""

    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('gemini', 'Google Gemini'),
        ('deepseek', 'DeepSeek'),
        ('anthropic', 'Anthropic (Claude)'),
        ('groq', 'Groq'),
        ('mistral', 'Mistral AI'),
        ('ollama', 'Ollama (Local)'),
        ('custom', 'Custom Provider'),
    ]

    provider = models.CharField(
        _('provider'),
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='openai',
    )
    api_key = models.CharField(
        _('API key'),
        max_length=500,
        blank=True,
        default='',
        help_text=_('API key for the selected provider. Leave blank to use environment variable.'),
    )
    model_name = models.CharField(
        _('model name'),
        max_length=100,
        default='gpt-4o-mini',
        help_text=_('e.g. gpt-4o-mini, gemini-2.0-flash, deepseek-chat'),
    )
    base_url = models.URLField(
        _('base URL'),
        blank=True,
        default='',
        help_text=_('Custom API base URL. Leave blank for provider default.'),
    )
    max_tokens = models.PositiveIntegerField(
        _('max tokens'),
        default=500,
    )
    temperature = models.DecimalField(
        _('temperature'),
        max_digits=3,
        decimal_places=2,
        default=0.3,
    )
    cache_ttl = models.PositiveIntegerField(
        _('cache TTL (seconds)'),
        default=86400,
        help_text=_('How long to cache AI responses (seconds).'),
    )
    daily_budget = models.DecimalField(
        _('daily budget (USD)'),
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text=_('Maximum daily spend limit in USD.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
    )
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('AI settings')
        verbose_name_plural = _('AI settings')

    def __str__(self) -> str:
        return f'{self.get_provider_display()} — {self.model_name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.apply_to_settings()

    def apply_to_settings(self):
        """Apply these settings to Django settings at runtime."""
        from django.conf import settings as django_settings
        django_settings.OPENAI_API_KEY = self.api_key
        django_settings.AI_MODEL = self.model_name
        django_settings.AI_MAX_TOKENS = self.max_tokens
        django_settings.AI_CACHE_TTL = self.cache_ttl
        django_settings.AI_DAILY_BUDGET = float(self.daily_budget)
        django_settings.AI_BASE_URL = self.base_url or None

    @classmethod
    def load(cls):
        """Load the singleton settings instance, creating defaults if needed."""
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'provider': 'openai',
                'model_name': 'gpt-4o-mini',
                'max_tokens': 500,
                'temperature': 0.3,
                'cache_ttl': 86400,
                'daily_budget': 1.00,
                'is_active': True,
            },
        )
        return obj
