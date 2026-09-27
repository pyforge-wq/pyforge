from __future__ import annotations

from enum import Enum

from pyforge.middleware import middleware_registry

from .router import Router


class RouteGroup:
    """Context manager returned by :meth:`Router.group`.

    Usage::

        with router.group(prefix="/api/v1", middleware=["auth"]) as group:
            group.get("/users", UserController.index, name="users.index")

    On exit, the group's routes are mounted onto the parent router via
    FastAPI's ``include_router`` (prefix + middleware become route
    dependencies), and any named routes are re-registered on the parent
    with the prefix and an optional dotted name prefix applied.
    """

    def __init__(
        self,
        parent: Router,
        *,
        prefix: str = "",
        middleware: list[str] | None = None,
        name: str | None = None,
        tags: list[str | Enum] | None = None,
    ) -> None:
        self._parent = parent
        self._prefix = prefix
        self._middleware = middleware or []
        self._name_prefix = name
        self._tags = tags
        self._router = Router(container=parent.container)

    def __enter__(self) -> Router:
        return self._router

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        if exc_type is not None:
            return
        dependencies = middleware_registry.resolve(self._middleware) if self._middleware else None
        self._parent.to_fastapi_router().include_router(
            self._router.to_fastapi_router(),
            prefix=self._prefix,
            dependencies=dependencies,
            tags=self._tags,
        )
        for name, path in self._router.named_routes.items():
            full_name = f"{self._name_prefix}.{name}" if self._name_prefix else name
            self._parent._named_routes[full_name] = f"{self._prefix}{path}"
