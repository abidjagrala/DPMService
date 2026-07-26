"""Smart data entry — auto-fill suggestions and duplicate detection."""

import logging

from django.utils import timezone

from clients.models import Client, Employee
from masters.models import City, ServiceType, State
from hosting.models import DomainHosting
from tickets.models import ServiceTicket

from .prompts import ADDRESS_SUGGEST_PROMPT, TICKET_SUGGEST_PROMPT
from .services import AIService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-Fill Suggestions
# ---------------------------------------------------------------------------

def suggest_ticket_fields(subject: str, description: str) -> dict:
    """Suggest priority, service_type, client, assignee from ticket text."""
    ai = AIService()

    service_types = list(ServiceType.objects.values_list('name', flat=True))
    clients = list(Client.objects.filter(is_active=True).values_list('company_name', flat=True))
    employees = list(
        Employee.objects.filter(is_active=True)
        .select_related('user')
        .values_list('user__first_name', 'user__last_name')
    )
    employees = [f'{f} {l}'.strip() for f, l in employees]

    result = ai.query(
        system_prompt=TICKET_SUGGEST_PROMPT.format(
            service_types=', '.join(service_types),
            clients=', '.join(clients[:50]),
            employees=', '.join(employees[:50]),
        ),
        user_prompt=f'Subject: {subject}\nDescription: {description}',
        max_tokens=200,
        feature='suggest_ticket',
    )
    return result


def suggest_from_address(address: str) -> dict:
    """Suggest city, state, pincode from an Indian address."""
    ai = AIService()

    cities = list(City.objects.filter(is_active=True).values_list('name', flat=True))
    states = list(State.objects.filter(is_active=True).values_list('name', flat=True))

    result = ai.query(
        system_prompt=ADDRESS_SUGGEST_PROMPT.format(
            cities=', '.join(cities[:100]),
            states=', '.join(states),
        ),
        user_prompt=f'Address: {address}',
        max_tokens=150,
        feature='suggest_address',
    )
    return result


# ---------------------------------------------------------------------------
# Duplicate Detection (no API cost — uses rapidfuzz)
# ---------------------------------------------------------------------------

class DuplicateDetector:
    """Fuzzy duplicate detection using rapidfuzz."""

    THRESHOLD = 80

    @staticmethod
    def check_client(company_name: str, email: str, phone: str) -> list:
        """Check for duplicate clients. Returns list of warnings."""
        from rapidfuzz import fuzz, process

        duplicates = []

        # Exact email
        if email and Client.objects.filter(email__iexact=email).exists():
            duplicates.append({
                'field': 'email',
                'message': f'A client with email {email} already exists.',
                'severity': 'high',
            })

        # Exact phone
        if phone and Client.objects.filter(phone=phone).exists():
            duplicates.append({
                'field': 'phone',
                'message': f'A client with phone {phone} already exists.',
                'severity': 'high',
            })

        # Fuzzy company name
        if company_name:
            existing = list(Client.objects.values_list('company_name', flat=True))
            if existing:
                match = process.extractOne(
                    company_name, existing, scorer=fuzz.token_sort_ratio
                )
                if match and match[1] >= DuplicateDetector.THRESHOLD:
                    duplicates.append({
                        'field': 'company_name',
                        'message': f'Similar client found: "{match[0]}" ({match[1]}% match).',
                        'severity': 'medium',
                        'suggestion': match[0],
                    })

        return duplicates

    @staticmethod
    def check_hosting(service_name: str, client_id: int) -> list:
        """Check for duplicate hosting services."""
        from rapidfuzz import fuzz, process

        if not service_name or not client_id:
            return []

        existing = list(
            DomainHosting.objects.filter(client_id=client_id)
            .values_list('service_name', flat=True)
        )
        if not existing:
            return []

        match = process.extractOne(
            service_name, existing, scorer=fuzz.token_set_ratio
        )
        if match and match[1] >= 85:
            return [{
                'field': 'service_name',
                'message': f'Similar service already tracked: "{match[0]}" ({match[1]}% match).',
                'severity': 'medium',
            }]
        return []

    @staticmethod
    def check_ticket(subject: str, client_id: int) -> list:
        """Check for duplicate open tickets from same client."""
        from rapidfuzz import fuzz, process

        if not subject or not client_id:
            return []

        open_tickets = list(
            ServiceTicket.objects.filter(
                client_id=client_id,
                status__in=['new', 'assigned', 'in_progress', 'on_hold'],
            ).values_list('subject', flat=True)
        )
        if not open_tickets:
            return []

        match = process.extractOne(
            subject, open_tickets, scorer=fuzz.token_set_ratio
        )
        if match and match[1] >= 80:
            return [{
                'field': 'subject',
                'message': f'Similar open ticket found: "{match[0]}" ({match[1]}% match).',
                'severity': 'medium',
            }]
        return []
