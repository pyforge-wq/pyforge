from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """A sane, opinionated default set of security response headers —
    ``app.use_middleware(SecurityHeadersMiddleware)``. Doesn't set a
    Content-Security-Policy by default (there's no sane one-size-fits-all
    value; pass yours via ``content_security_policy=`` if you want one set),
    and only sets HSTS on requests that already arrived over HTTPS (setting
    it on plain HTTP is a no-op per spec, but skipping it there avoids
    implying HTTPS is available when the request shows it might not be).
    Sets every header with ``setdefault`` — never overrides one your own
    code already set."""

    def __init__(
        self,
        app: Any,
        *,
        content_security_policy: str | None = None,
        hsts_max_age: int = 31536000,
    ) -> None:
        super().__init__(app)
        self.content_security_policy = content_security_policy
        self.hsts_max_age = hsts_max_age

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        if self.content_security_policy:
            response.headers.setdefault("Content-Security-Policy", self.content_security_policy)
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", f"max-age={self.hsts_max_age}; includeSubDomains"
            )
        return response
