from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request

from pyforge.cache import Cache
from pyforge.routing import inject_dependency

_PERIOD_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def _parse_rate(rate: str) -> tuple[int, int]:
    """``"60/minute"`` -> ``(60, 60)``."""
    count_str, _, period = rate.partition("/")
    if not period:
        raise ValueError(f"Rate must look like '60/minute', got '{rate}'.")
    seconds = _PERIOD_SECONDS.get(period)
    if seconds is None:
        raise ValueError(f"Unknown rate limit period '{period}' — use second/minute/hour/day.")
    return int(count_str), seconds


def rate_limit(
    rate: str,
    *,
    key_func: Callable[[Request], str] | None = None,
    cache: Cache | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: ``@rate_limit("60/minute")`` — 429s once more than the
    given count of requests from the same key (default: client IP) happen
    within the window::

        class LoginController:
            @rate_limit("5/minute")
            async def attempt(self, request: LoginRequest) -> dict:
                ...

    A fixed-window counter stored in `cache` (default: `pyforge.cache.default_cache()`)
    — simple, and not perfectly precise at window boundaries (a client could
    send up to ~2x the limit split across one), but exact sliding-window
    rate limiting needs meaningfully more infrastructure than a decorator;
    reach for a dedicated rate-limiting service/proxy if you need that
    precision. Requires the optional cache module (and its `redis` extra if
    you want the limit to apply across more than one process).
    """
    limit, window_seconds = _parse_rate(rate)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def check(request: Request) -> None:
            from pyforge.cache import default_cache

            store = cache or default_cache()
            client_key = key_func(request) if key_func else (request.client.host if request.client else "unknown")
            window = int(time.time() // window_seconds)
            cache_key = f"rate_limit:{func.__qualname__}:{client_key}:{window}"

            current = store.get(cache_key, 0)
            if current >= limit:
                raise HTTPException(status_code=429, detail="Too Many Requests")
            store.put(cache_key, current + 1, ttl=window_seconds)

        return inject_dependency(func, check, param_name="_pyforge_rate_limit_check")

    return decorator
