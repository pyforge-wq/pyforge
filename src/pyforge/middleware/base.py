from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends
from fastapi.params import Depends as DependsType

DependencyCallable = Callable[..., Any]


class MiddlewareRegistry:
    """Maps short middleware names (as used in ``router.group(middleware=[...])``)
    to FastAPI dependency callables.

    This covers route-scoped "guard" style middleware (auth checks, tenant
    resolution, rate limiting), addressed by name. Global, ASGI-level
    middleware (CORS, security headers, GZip, ...) doesn't need a name: use
    the standard FastAPI/Starlette ``app.fastapi.add_middleware(...)`` API
    directly, exposed as :meth:`pyforge.core.PyForge.use_middleware`.
    """

    def __init__(self) -> None:
        self._middleware: dict[str, DependencyCallable] = {}

    def register(self, name: str, dependency: DependencyCallable) -> None:
        self._middleware[name] = dependency

    def has(self, name: str) -> bool:
        return name in self._middleware

    def resolve(self, names: list[str]) -> list[DependsType]:
        resolved = []
        for name in names:
            if name not in self._middleware:
                raise KeyError(
                    f"Unknown middleware '{name}'. Register it first with "
                    f"app.middleware.register('{name}', dependency)."
                )
            resolved.append(Depends(self._middleware[name]))
        return resolved


middleware_registry = MiddlewareRegistry()
"""Process-wide default middleware registry, mirroring :data:`pyforge.container.container`."""
