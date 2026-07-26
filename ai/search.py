"""Natural Language Search — translates user queries to Django Q filters."""

import logging

from django.db.models import Q
from django.utils import timezone

from clients.models import Client, Employee
from hosting.models import AnnualMaintenanceContract, DomainHosting
from masters.models import ServiceType
from tickets.models import ServiceTicket

from .prompts import SEARCH_SYSTEM_PROMPT
from .services import AIService

logger = logging.getLogger(__name__)

# Whitelisted fields per model (prevents injection)
ALLOWED_FIELDS = {
    'ServiceTicket': {
        'ticket_number', 'subject', 'description', 'status', 'priority',
        'client__company_name', 'client__city__name', 'client__branch__name',
        'assigned_to__user__first_name', 'assigned_to__user__last_name',
        'scheduled_date', 'created_at', 'service_type__name',
    },
    'DomainHosting': {
        'service_name', 'service_type', 'status', 'client__company_name',
        'provider', 'expiry_date', 'renewal_amount', 'registration_date',
    },
    'Client': {
        'company_name', 'contact_person', 'phone', 'email',
        'city__name', 'state__name', 'is_active', 'gst_number',
    },
    'Employee': {
        'user__first_name', 'user__last_name', 'user__email',
        'employee_id', 'department', 'designation', 'is_active',
    },
    'AnnualMaintenanceContract': {
        'title', 'client__company_name', 'payment_status',
        'expiry_date', 'amount', 'is_active',
    },
}

# Model name → queryset mapping
MODEL_QUERYSETS = {
    'ServiceTicket': lambda: ServiceTicket.objects.select_related(
        'service_type', 'client', 'client__city', 'assigned_to__user',
    ).all(),
    'DomainHosting': lambda: DomainHosting.objects.select_related('client').all(),
    'Client': lambda: Client.objects.select_related('city', 'state').all(),
    'Employee': lambda: Employee.objects.select_related('user', 'city', 'state').all(),
    'AnnualMaintenanceContract': lambda: AnnualMaintenanceContract.objects.select_related('client').all(),
}


def translate_query(query: str, model_hint: str = '') -> dict:
    """Use AI to translate a natural language query into structured filters."""
    ai = AIService()

    user_prompt = f'Translate this search query: {query}'
    if model_hint:
        user_prompt += f'\nFocus on model: {model_hint}'

    result = ai.query(
        system_prompt=SEARCH_SYSTEM_PROMPT.format(current_date=timezone.now().date()),
        user_prompt=user_prompt,
        max_tokens=250,
        feature='search',
    )

    if 'error' in result:
        return {'error': result['error']}

    # Validate fields
    model_name = result.get('model', 'ServiceTicket')
    allowed = ALLOWED_FIELDS.get(model_name, set())
    validated_filters = []

    for f in result.get('filters', []):
        field = f.get('field', '')
        if field in allowed:
            validated_filters.append(f)
        else:
            logger.warning('AI suggested invalid field: %s.%s', model_name, field)

    result['filters'] = validated_filters
    return result


def apply_filters(queryset, filters: list) -> 'QuerySet':
    """Apply AI-generated filters to a Django queryset."""
    for f in filters:
        field = f.get('field', '')
        op = f.get('op', 'exact')
        value = f.get('value')

        if value is None or value == '':
            continue

        # Build the lookup
        lookup = f'{field}__{op}' if op != 'exact' else field
        try:
            queryset = queryset.filter(**{lookup: value})
        except Exception as e:
            logger.warning('Filter error (%s=%s): %s', lookup, value, e)

    return queryset


def get_model_queryset(model_name: str):
    """Return the base queryset for a given model name."""
    factory = MODEL_QUERYSETS.get(model_name)
    if factory:
        return factory()
    return ServiceTicket.objects.none()
