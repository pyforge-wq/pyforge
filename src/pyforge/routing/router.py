from __future__ import annotations

import inspect
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends

from pyforge.container import Container
from pyforge.container import container as default_container
from pyforge.validation import FormRequest

if TYPE_CHECKING:
    from .group import RouteGroup

Handler = Callable[..., Any]


def _is_form_request_param(parameter: inspect.Parameter) -> bool:
    return (
        parameter.default is inspect.Parameter.empty
        and isinstance(parameter.annotation, type)
        and issubclass(parameter.annotation, FormRequest)
    )


def _inject_form_request_defaults(signature: inspect.Signature) -> inspect.Signature:
    """A parameter typed as a ``FormRequest`` subclass with no explicit
    default becomes a FastAPI dependency automatically — see
    :class:`pyforge.validation.FormRequest`."""
    new_params = [
        parameter.replace(default=Depends(parameter.annotation._as_dependency))
        if _is_form_request_param(parameter)
        else parameter
        for parameter in signature.parameters.values()
    ]
    return signature.replace(parameters=new_params)


class Router:
    """A convention-driven routing surface over a FastAPI ``APIRouter``.

    Plain functions are registered as-is — FastAPI handles them natively,
    including its own dependency injection and parameter inference. A
    *controller action* (a method looked up off a class, e.g.
    ``UserController.show``) is detected automatically and wrapped so the
    controller is resolved fresh from the container on every request, while
    the wrapped endpoint keeps the original method's signature (minus
    ``self``) so FastAPI can still introspect path/query params, bodies, and
    dependencies exactly as if it were a plain function.
    """

    def __init__(self, *, container: Container | None = None) -> None:
        self._container = container or default_container
        self._api_router = APIRouter()
        self._named_routes: dict[str, str] = {}

    @property
    def container(self) -> Container:
        return self._container

    @property
    def named_routes(self) -> dict[str, str]:
        return dict(self._named_routes)

    def to_fastapi_router(self) -> APIRouter:
        return self._api_router

    def _add_route(
        self,
        method: str,
        path: str,
        handler: Handler,
        *,
        name: str | None = None,
        **fastapi_kwargs: Any,
    ) -> Router:
        endpoint = self._resolve_handler(handler)
        add_route = getattr(self._api_router, method)
        add_route(path, name=name, **fastapi_kwargs)(endpoint)
        if name:
            self._named_routes[name] = path
        return self

    def get(self, path: str, handler: Handler, *, name: str | None = None, **kwargs: Any) -> Router:
        return self._add_route("get", path, handler, name=name, **kwargs)

    def post(self, path: str, handler: Handler, *, name: str | None = None, **kwargs: Any) -> Router:
        return self._add_route("post", path, handler, name=name, **kwargs)

    def put(self, path: str, handler: Handler, *, name: str | None = None, **kwargs: Any) -> Router:
        return self._add_route("put", path, handler, name=name, **kwargs)

    def patch(self, path: str, handler: Handler, *, name: str | None = None, **kwargs: Any) -> Router:
        return self._add_route("patch", path, handler, name=name, **kwargs)

    def delete(self, path: str, handler: Handler, *, name: str | None = None, **kwargs: Any) -> Router:
        return self._add_route("delete", path, handler, name=name, **kwargs)

    def options(self, path: str, handler: Handler, *, name: str | None = None, **kwargs: Any) -> Router:
        return self._add_route("options", path, handler, name=name, **kwargs)

    def head(self, path: str, handler: Handler, *, name: str | None = None, **kwargs: Any) -> Router:
        return self._add_route("head", path, handler, name=name, **kwargs)

    def websocket(self, path: str, handler: Handler, *, name: str | None = None) -> Router:
        endpoint = self._resolve_handler(handler)
        self._api_router.add_api_websocket_route(path, endpoint, name=name)
        if name:
            self._named_routes[name] = path
        return self

    def group(
        self,
        *,
        prefix: str = "",
        middleware: list[str] | None = None,
        name: str | None = None,
        tags: list[str | Enum] | None = None,
    ) -> RouteGroup:
        from .group import RouteGroup

        return RouteGroup(self, prefix=prefix, middleware=middleware, name=name, tags=tags)

    def url(self, route_name: str, **params: Any) -> str:
        path = self._named_routes.get(route_name)
        if path is None:
            raise KeyError(f"No route named '{route_name}'.")
        return path.format(**params)

    def _resolve_handler(self, handler: Handler) -> Handler:
        owner = self._controller_class_of(handler)
        if owner is not None:
            return self._wrap_controller_action(owner, handler)
        return self._maybe_wrap_for_form_requests(handler)

    @staticmethod
    def _maybe_wrap_for_form_requests(handler: Handler) -> Handler:
        try:
            signature = inspect.signature(handler)
        except (TypeError, ValueError):
            return handler
        if not any(_is_form_request_param(p) for p in signature.parameters.values()):
            return handler

        new_signature = _inject_form_request_defaults(signature)

        if inspect.iscoroutinefunction(handler):

            async def endpoint(*args: Any, **kwargs: Any) -> Any:
                return await handler(*args, **kwargs)

        else:

            def endpoint(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
                return handler(*args, **kwargs)

        endpoint.__signature__ = new_signature  # type: ignore[attr-defined]
        endpoint.__name__ = getattr(handler, "__name__", "endpoint")
        endpoint.__doc__ = handler.__doc__
        return endpoint

    @staticmethod
    def _controller_class_of(handler: Handler) -> type | None:
        """Detect ``handler`` being an unbound method reference like
        ``UserController.show`` (as opposed to a plain module-level function
        or a lambda)."""
        qualname = getattr(handler, "__qualname__", "")
        if "." not in qualname or "<locals>" in qualname:
            return None
        try:
            params = list(inspect.signature(handler).parameters.values())
        except (TypeError, ValueError):
            return None
        if not params or params[0].name != "self":
            return None
        module = inspect.getmodule(handler)
        if module is None:
            return None
        cls_name = qualname.rsplit(".", 1)[0]
        cls = getattr(module, cls_name, None)
        return cls if inspect.isclass(cls) else None

    def _wrap_controller_action(self, owner: type, method: Handler) -> Handler:
        container = self._container
        signature = inspect.signature(method)
        new_params = list(signature.parameters.values())[1:]
        new_signature = _inject_form_request_defaults(signature.replace(parameters=new_params))

        if inspect.iscoroutinefunction(method):

            async def endpoint(*args: Any, **kwargs: Any) -> Any:
                controller: Any = container.make(owner)
                bound = getattr(controller, method.__name__)
                return await bound(*args, **kwargs)

        else:

            def endpoint(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
                controller: Any = container.make(owner)
                bound = getattr(controller, method.__name__)
                return bound(*args, **kwargs)

        endpoint.__signature__ = new_signature  # type: ignore[attr-defined]
        endpoint.__name__ = method.__name__
        endpoint.__doc__ = method.__doc__
        return endpoint
