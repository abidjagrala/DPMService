from django.contrib import admin

from .models import AICacheEntry, AIUsageLog


@admin.register(AICacheEntry)
class AICacheEntryAdmin(admin.ModelAdmin):
    list_display = ('prompt_hash', 'model', 'tokens_input', 'tokens_output', 'created_at', 'expires_at')
    list_filter = ('model',)
    search_fields = ('prompt_hash',)
    readonly_fields = ('prompt_hash', 'response', 'model', 'tokens_input', 'tokens_output', 'created_at', 'expires_at')


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ('feature', 'model', 'tokens_input', 'tokens_output', 'cost_estimate', 'success', 'created_at')
    list_filter = ('feature', 'model', 'success')
    search_fields = ('feature',)
    readonly_fields = ('feature', 'model', 'tokens_input', 'tokens_output', 'cost_estimate', 'response_time_ms', 'success', 'error_message', 'created_at')
