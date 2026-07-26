"""Ticket auto-classification using AI."""

import logging

from masters.models import ServiceType
from .prompts import CLASSIFY_TICKET_PROMPT
from .services import AIService

logger = logging.getLogger(__name__)


def classify_ticket(subject: str, description: str, client_name: str) -> dict:
    """Classify a ticket by priority, service type, and effort."""
    ai = AIService()

    service_types = list(ServiceType.objects.values_list('name', flat=True))

    result = ai.query(
        system_prompt=CLASSIFY_TICKET_PROMPT.format(
            subject=subject,
            description=description or '(no description)',
            client_name=client_name or 'Unknown',
            service_types=', '.join(service_types),
        ),
        user_prompt=f'Classify this ticket: {subject}',
        max_tokens=200,
        feature='classify',
    )
    return result
