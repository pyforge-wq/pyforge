from __future__ import annotations

from .cache import Cache

_default_cache: Cache | None = None


def set_default_cache(cache: Cache) -> None:
    """Registers the process-wide default ``Cache`` — typically from a
    service provider's ``register()``, right after building it with
    :func:`~pyforge.cache.make_cache`."""
    global _default_cache
    _default_cache = cache


def default_cache() -> Cache:
    if _default_cache is None:
        raise RuntimeError(
            "No default Cache configured. Call set_default_cache(make_cache(config('cache'))) "
            "once, e.g. from a service provider's register()."
        )
    return _default_cache
