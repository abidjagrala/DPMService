"""Smart suggestions engine — proactive recommendations."""

import json
import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from clients.models import Client, Employee
from hosting.models import AnnualMaintenanceContract, DomainHosting
from tickets.models import ServiceTicket

from .prompts import SUGGESTION_PROMPT
from .services import AIService

logger = logging.getLogger(__name__)

CACHE_KEY = 'dashboard_ai_suggestions'
CACHE_TTL = 3600  # 1 hour


def generate_suggestions() -> list:
    """Generate a combined list of rule-based + AI suggestions."""
    suggestions = []

    suggestions.extend(_expiring_domains())
    suggestions.extend(_expiring_amcs())
    suggestions.extend(_overdue_tickets())
    suggestions.extend(_idle_employees())
    suggestions.extend(_ai_pattern_suggestions())

    cache.set(CACHE_KEY, suggestions, CACHE_TTL)
    return suggestions


def get_suggestions() -> list:
    """Get cached suggestions or generate fresh ones."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    return generate_suggestions()


# ---------------------------------------------------------------------------
# Rule-based suggestions
# ---------------------------------------------------------------------------

def _expiring_domains() -> list:
    today = timezone.now().date()
    expiring = DomainHosting.objects.filter(
        expiry_date__lte=today + timedelta(days=7),
        is_active=True,
    ).select_related('client')

    return [
        {
            'type': 'domain_expiry',
            'title': f'Domain expiring: {d.service_name}',
            'description': f'Expires on {d.expiry_date}. Create renewal ticket.',
            'client': d.client.company_name,
            'action_url': f'/hosting/{d.pk}/',
            'priority': 'high' if d.expiry_date <= today else 'medium',
        }
        for d in expiring
    ]


def _expiring_amcs() -> list:
    today = timezone.now().date()
    expiring = AnnualMaintenanceContract.objects.filter(
        expiry_date__lte=today + timedelta(days=30),
        is_active=True,
        payment_status__in=['pending', 'partial', 'overdue'],
    ).select_related('client')

    return [
        {
            'type': 'amc_expiry',
            'title': f'AMC expiring: {a.title}',
            'description': f'Expires on {a.expiry_date} — {a.get_payment_status_display()}.',
            'client': a.client.company_name,
            'action_url': f'/hosting/amc/{a.pk}/',
            'priority': 'high' if a.expiry_date <= today + timedelta(days=7) else 'medium',
        }
        for a in expiring
    ]


def _overdue_tickets() -> list:
    today = timezone.now().date()
    overdue = ServiceTicket.objects.filter(
        scheduled_date__lt=today,
        status__in=['new', 'assigned', 'in_progress', 'on_hold'],
    ).select_related('client', 'assigned_to__user')

    return [
        {
            'type': 'overdue_ticket',
            'title': f'Overdue: {t.ticket_number}',
            'description': (
                f'Scheduled for {t.scheduled_date}. '
                f'Assigned to {t.assigned_to.user.get_full_name() if t.assigned_to else "Unassigned"}.'
            ),
            'client': t.client.company_name,
            'action_url': f'/tickets/{t.pk}/',
            'priority': 'high',
        }
        for t in overdue
    ]


def _idle_employees() -> list:
    cutoff = timezone.now() - timedelta(days=14)
    active_employees = Employee.objects.filter(is_active=True).select_related('user')

    idle = []
    for emp in active_employees:
        recent_tickets = ServiceTicket.objects.filter(
            assigned_to=emp,
            created_at__gte=cutoff,
        ).exists()
        if not recent_tickets:
            idle.append(emp)

    return [
        {
            'type': 'idle_employee',
            'title': f'Idle: {e.user.get_full_name()}',
            'description': f'No tickets assigned in 14 days. Consider assigning pending work.',
            'client': '',
            'action_url': '/clients/employees/',
            'priority': 'low',
        }
        for e in idle[:5]
    ]


# ---------------------------------------------------------------------------
# AI-powered pattern suggestions
# ---------------------------------------------------------------------------

def _ai_pattern_suggestions() -> list:
    """Use AI to analyze patterns in recent ticket data."""
    cutoff = timezone.now() - timedelta(days=30)
    recent = list(
        ServiceTicket.objects.filter(created_at__gte=cutoff)
        .values('client__company_name', 'status', 'priority', 'subject')
    )

    if not recent:
        return []

    ai = AIService()
    result = ai.query(
        system_prompt=SUGGESTION_PROMPT,
        user_prompt=f'Analyze this ticket data and suggest actions:\n{json.dumps(recent[:50])}',
        max_tokens=300,
        feature='suggestions',
    )

    if 'error' in result:
        return []

    return [
        {
            'type': s.get('type', 'general'),
            'title': s.get('title', 'Suggestion'),
            'description': s.get('description', ''),
            'client': '',
            'action_url': '/tickets/',
            'priority': s.get('priority', 'medium'),
        }
        for s in result.get('suggestions', [])
    ]
