from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from fastapi import FastAPI

from pyforge.config import Config, load_env, set_active_config
from pyforge.container import Container
from pyforge.container import container as default_container
from pyforge.database import DatabaseManager, DatabaseSessionMiddleware, set_current_database
from pyforge.middleware import middleware_registry
from pyforge.providers import ServiceProvider
from pyforge.routing import Router

from .exception_handlers import register_exception_handlers

P = TypeVar("P", bound=ServiceProvider)


class PyForge:
    """The application: a thin, opinionated shell around a FastAPI instance.

    PyForge does not replace FastAPI — it wires up the pieces a growing
    application eventually needs by hand (a DI container, config loaded from
    ``.env``/``config/*.py``, named/grouped routing, service providers) and
    then gets out of the way. ``app.fastapi`` is always the real
    ``fastapi.FastAPI`` instance, and ``PyForge`` itself is ASGI-callable
    (``uvicorn main:app`` works directly), so any native FastAPI feature —
    middleware, dependencies, routers, background tasks, responses — works
    unmodified alongside it.

    If ``config/database.py`` exists, a :class:`~pyforge.database.DatabaseManager`
    is built from it automatically and a session is opened around every HTTP
    request — see docs/architecture/06-database-architecture.md — so
    ``Model`` methods (``User.create(...)``, ``User.find(1)``, ...) work in
    any controller with no explicit wiring.
    """

    def __init__(
        self,
        *,
        base_path: str | Path | None = None,
        container: Container | None = None,
        title: str = "PyForge Application",
        **fastapi_kwargs: Any,
    ) -> None:
        self.base_path = Path(base_path) if base_path is not None else Path.cwd()
        self.container = container or default_container
        self.container.instance(PyForge, self)

        env_file = self.base_path / ".env"
        if env_file.exists():
            load_env(env_file)

        self.config = Config.load_directory(self.base_path / "config")
        set_active_config(self.config)
        self.container.instance(Config, self.config)

        self.middleware = middleware_registry

        self.database: DatabaseManager | None = None
        database_config = self.config.get("database")
        if database_config is not None:
            self.database = DatabaseManager(database_config)
            set_current_database(self.database)
            self.container.instance(DatabaseManager, self.database)

        self._providers: list[ServiceProvider] = []
        self._booted = False

        user_lifespan = fastapi_kwargs.pop("lifespan", None)

        @asynccontextmanager
        async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
            self.boot()
            if user_lifespan is not None:
                async with user_lifespan(self._fastapi):
                    yield
            else:
                yield

        self._fastapi = FastAPI(title=title, lifespan=_lifespan, **fastapi_kwargs)
        self.container.instance(FastAPI, self._fastapi)
        register_exception_handlers(self)

        if self.database is not None:
            self.use_middleware(DatabaseSessionMiddleware)

    @property
    def fastapi(self) -> FastAPI:
        """The underlying FastAPI application. Use it for anything PyForge
        doesn't wrap: ``app.fastapi.add_exception_handler(...)``, etc."""
        return self._fastapi

    @property
    def fastapi_app(self) -> FastAPI:
        """Alias of :attr:`fastapi`."""
        return self._fastapi

    def register_routes(
        self, router: Router, *, prefix: str = "", tags: list[str | Enum] | None = None
    ) -> PyForge:
        self._fastapi.include_router(router.to_fastapi_router(), prefix=prefix, tags=tags)
        return self

    def use_middleware(self, middleware_class: Any, **options: Any) -> PyForge:
        """Register global, ASGI-level middleware — a direct passthrough to
        ``FastAPI.add_middleware``. For route-scoped named middleware
        (``router.group(middleware=["auth"])``), use ``app.middleware.register``."""
        self._fastapi.add_middleware(middleware_class, **options)
        return self

    def register(self, provider_class: type[P]) -> P:
        """Instantiate a service provider, call its ``register()`` immediately,
        and queue it for ``boot()`` (run once, on application startup)."""
        provider = provider_class(self)
        provider.register()
        self._providers.append(provider)
        return provider

    def boot(self) -> None:
        """Run ``boot()`` on every registered provider that hasn't booted yet.
        Called automatically on FastAPI startup, but safe to call directly
        (e.g. in tests that don't go through a real ASGI lifecycle)."""
        if self._booted:
            return
        for provider in self._providers:
            provider.boot()
        self._booted = True

    def make(self, abstract: Any, **params: Any) -> Any:
        """Shorthand for ``app.container.make(...)``."""
        return self.container.make(abstract, **params)

    def get(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.post(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.put(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.patch(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.delete(path, **kwargs)

    def options(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.options(path, **kwargs)

    def head(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.head(path, **kwargs)

    def websocket(self, path: str, **kwargs: Any) -> Callable:
        return self._fastapi.websocket(path, **kwargs)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self._fastapi(scope, receive, send)
