from django.contrib import admin

from .models import DomainHosting, DomainHostingInvoice


class DomainHostingInvoiceInline(admin.TabularInline):
    model = DomainHostingInvoice
    extra = 0


@admin.register(DomainHosting)
class DomainHostingAdmin(admin.ModelAdmin):
    list_display = [
        'service_name', 'client', 'service_type', 'provider',
        'expiry_date', 'status', 'reminder_sent', 'is_active',
    ]
    list_filter = ['service_type', 'status', 'is_active', 'reminder_sent']
    search_fields = ['service_name', 'client__company_name', 'provider']
    inlines = [DomainHostingInvoiceInline]


@admin.register(DomainHostingInvoice)
class DomainHostingInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'service', 'invoice_date', 'amount', 'paid']
    list_filter = ['paid']
    search_fields = ['invoice_number', 'service__service_name']
