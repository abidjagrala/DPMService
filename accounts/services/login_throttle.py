from django.core.cache import cache

MAX_ATTEMPTS = 10
LOCKOUT_SECONDS = 300  # 5 minutes


def _cache_key(email, ip):
    return f'login_attempts_{email.lower()}_{ip}'


def record_failed_attempt(email, ip):
    key = _cache_key(email, ip)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, LOCKOUT_SECONDS)
    return attempts


def is_locked_out(email, ip):
    key = _cache_key(email, ip)
    attempts = cache.get(key, 0)
    return attempts >= MAX_ATTEMPTS


def reset_attempts(email, ip):
    cache.delete(_cache_key(email, ip))


def get_remaining_attempts(email, ip):
    key = _cache_key(email, ip)
    attempts = cache.get(key, 0)
    return max(0, MAX_ATTEMPTS - attempts)
