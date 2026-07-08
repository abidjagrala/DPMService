from django.contrib import admin

from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
