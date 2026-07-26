import hashlib
import json
import logging
import time

from django.conf import settings
from django.utils import timezone

from openai import OpenAI

from .models import AICacheEntry, AIUsageLog

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (gpt-4o-mini)
INPUT_PRICE_PER_M = 0.15
OUTPUT_PRICE_PER_M = 0.60


class AIService:
    """Central OpenAI client with caching and cost controls."""

    def __init__(self):
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.model = getattr(settings, 'AI_MODEL', 'gpt-4o-mini')
        self.max_tokens = getattr(settings, 'AI_MAX_TOKENS', 500)
        self.cache_ttl = getattr(settings, 'AI_CACHE_TTL', 86400)
        self.client = OpenAI(api_key=api_key) if api_key else None

    def query(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float = 0.3,
        feature: str = 'general',
        use_cache: bool = True,
    ) -> dict:
        """Send prompt to OpenAI with caching. Returns parsed JSON."""
        if not self.client:
            return {'error': 'OpenAI API key not configured.'}

        tokens_budget = max_tokens or self.max_tokens
        prompt_hash = self._hash(system_prompt + user_prompt)

        # 1. Check cache
        if use_cache:
            cached = self._get_cached(prompt_hash)
            if cached:
                return cached

        # 2. Call API
        start = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                max_tokens=tokens_budget,
                temperature=temperature,
                response_format={'type': 'json_object'},
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._log_usage(
                feature=feature,
                tokens_input=0,
                tokens_output=0,
                response_time_ms=elapsed_ms,
                success=False,
                error=str(e),
            )
            return {'error': str(e)}

        # 3. Parse
        raw = response.choices[0].message.content
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {'raw': raw}

        # 4. Extract token counts
        usage = response.usage or {}
        tokens_in = getattr(usage, 'prompt_tokens', 0)
        tokens_out = getattr(usage, 'completion_tokens', 0)

        # 5. Cache
        if use_cache:
            self._set_cache(prompt_hash, result, tokens_in, tokens_out)

        # 6. Log
        self._log_usage(
            feature=feature,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            response_time_ms=elapsed_ms,
            success=True,
        )

        return result

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _get_cached(self, prompt_hash: str) -> dict | None:
        try:
            entry = AICacheEntry.objects.get(prompt_hash=prompt_hash)
            if not entry.is_expired:
                return entry.response
            entry.delete()
        except AICacheEntry.DoesNotExist:
            pass
        return None

    def _set_cache(self, prompt_hash: str, response: dict, tokens_in: int, tokens_out: int):
        AICacheEntry.objects.update_or_create(
            prompt_hash=prompt_hash,
            defaults={
                'response': response,
                'model': self.model,
                'tokens_input': tokens_in,
                'tokens_output': tokens_out,
                'expires_at': timezone.now() + timezone.timedelta(seconds=self.cache_ttl),
            },
        )

    # ------------------------------------------------------------------
    # Usage logging
    # ------------------------------------------------------------------

    def _log_usage(self, feature, tokens_input, tokens_output, response_time_ms, success, error=''):
        cost = (tokens_input * INPUT_PRICE_PER_M + tokens_output * OUTPUT_PRICE_PER_M) / 1_000_000
        AIUsageLog.objects.create(
            feature=feature,
            model=self.model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_estimate=cost,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error,
        )
