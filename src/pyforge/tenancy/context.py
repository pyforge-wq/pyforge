from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_current_tenant_id: ContextVar[Any | None] = ContextVar("pyforge_tenant_id", default=None)


def set_current_tenant(tenant_id: Any | None) -> None:
    """Sets the tenant for the current context (request, task, ...).
    Usually you want :func:`tenant_scope` or a resolution middleware instead
    of calling this directly."""
    _current_tenant_id.set(tenant_id)


def current_tenant_id() -> Any:
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        raise RuntimeError(
            "No current tenant set. Call set_current_tenant(...)/tenant_scope(...) first, "
            "or add a tenant-resolution middleware."
        )
    return tenant_id


def current_tenant_id_or_none() -> Any | None:
    return _current_tenant_id.get()


@contextmanager
def tenant_scope(tenant_id: Any) -> Iterator[None]:
    """``with tenant_scope(tenant_id): ...`` — sets the current tenant for
    the duration of the block, restoring whatever it was before on exit."""
    token = _current_tenant_id.set(tenant_id)
    try:
        yield
    finally:
        _current_tenant_id.reset(token)
