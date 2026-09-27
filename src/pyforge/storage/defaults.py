from __future__ import annotations

from .storage import Storage

_default_storage: Storage | None = None


def set_default_storage(storage: Storage) -> None:
    """Registers the process-wide default ``Storage`` — typically from a
    service provider's ``register()``, right after :func:`make_storage`."""
    global _default_storage
    _default_storage = storage


def default_storage() -> Storage:
    if _default_storage is None:
        raise RuntimeError(
            "No default Storage configured. Call set_default_storage(make_storage(config('storage'))) "
            "once, e.g. from a service provider's register()."
        )
    return _default_storage
