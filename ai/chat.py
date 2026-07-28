"""Conversational chat interface for querying data."""

import json
import logging

from django.db.models import Q
from django.utils import timezone

from clients.models import Client, Employee
from hosting.models import AnnualMaintenanceContract, DomainHosting
from tickets.models import ServiceTicket
from assets.models import Asset

from .prompts import CHAT_SYSTEM_PROMPT
from .services import AIService

logger = logging.getLogger(__name__)

# Whitelist of safe ORM operations
ALLOWED_MODELS = {
    'ServiceTicket': ServiceTicket,
    'DomainHosting': DomainHosting,
    'AnnualMaintenanceContract': AnnualMaintenanceContract,
    'Client': Client,
    'Employee': Employee,
    'Asset': Asset,
}


class AIChat:
    """Stateful chat that maintains conversation context."""

    def __init__(self):
        self.ai = AIService()
        self.messages = []  # last N messages for context

    def ask(self, question: str) -> dict:
        """Process a user question and return a response."""
        self.messages.append({'role': 'user', 'content': question})
        self.messages = self.messages[-6:]  # keep last 6 (3 pairs)

        context = '\n'.join(f'{m["role"]}: {m["content"]}' for m in self.messages)

        result = self.ai.query(
            system_prompt=CHAT_SYSTEM_PROMPT.format(current_date=timezone.now().date()),
            user_prompt=f'Conversation:\n{context}\n\nLatest: {question}',
            max_tokens=400,
            feature='chat',
        )

        if 'error' in result:
            return {'error': result['error'], 'natural_response': f"AI Error: {result['error']}"}

        if 'raw' in result and 'natural_response' not in result:
            return {'natural_response': f"Unexpected AI response. Raw: {result.get('raw', '')[:500]}"}

        # Try to execute ORM filters if provided
        data = None
        filters = result.get('suggested_orm_filters', {})
        model_name = filters.pop('_model', 'ServiceTicket') if isinstance(filters, dict) else 'ServiceTicket'

        if filters and isinstance(filters, dict) and model_name in ALLOWED_MODELS:
            try:
                qs = ALLOWED_MODELS[model_name].objects.all()
                for k, v in filters.items():
                    if isinstance(v, list):
                        qs = qs.filter(**{k: v})
                    else:
                        qs = qs.filter(**{k: v})
                data = list(qs[:20].values())
            except Exception as e:
                logger.warning('Chat ORM error: %s', e)

        response_text = result.get('natural_response', '')
        self.messages.append({'role': 'assistant', 'content': response_text})

        return {
            'natural_response': response_text,
            'data': data,
            'query_type': result.get('query_type', ''),
            'understanding': result.get('understanding', ''),
        }
