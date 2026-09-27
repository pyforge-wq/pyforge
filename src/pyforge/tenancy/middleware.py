from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import tenant_scope

TenantResolver = Callable[[Request], Any]


def subdomain_tenant_resolver(request: Request) -> str | None:
    """``acme.myapp.com`` -> ``"acme"``. Returns ``None`` for a bare/2-label
    host (``myapp.com``, ``localhost``) — no subdomain to resolve."""
    host = request.headers.get("host", "").split(":")[0]
    parts = host.split(".")
    return parts[0] if len(parts) > 2 else None


def header_tenant_resolver(header_name: str = "X-Tenant-ID") -> TenantResolver:
    def resolve(request: Request) -> str | None:
        return request.headers.get(header_name)

    return resolve


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Resolves the current tenant once per request (via ``resolver``, e.g.
    :func:`subdomain_tenant_resolver` or :func:`header_tenant_resolver`) and
    makes it available through :func:`~pyforge.tenancy.current_tenant_id` for
    the rest of that request — the multi-tenant counterpart to
    :class:`pyforge.database.DatabaseSessionMiddleware`, and typically added
    alongside it: ``app.use_middleware(TenantResolutionMiddleware, resolver=...)``.
    """

    def __init__(self, app: Any, *, resolver: TenantResolver) -> None:
        super().__init__(app)
        self.resolver = resolver

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        tenant_id = self.resolver(request)
        with tenant_scope(tenant_id):
            return await call_next(request)
