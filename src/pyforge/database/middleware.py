from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .session import session_scope


class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    """Opens a :func:`~pyforge.database.session_scope` around every HTTP
    request, so ``Model`` methods (``User.create(...)``, ``User.find(1)``,
    ...) work inside any controller with no explicit session dependency —
    committed on a successful response, rolled back if the handler raises.

    Registered automatically by :class:`pyforge.core.Application` whenever
    ``config/database.py`` is present; never needed by hand.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        with session_scope():
            return await call_next(request)
