from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request

from pyforge.routing import inject_dependency

from .guard import Auth

_default_auth: Auth | None = None


def set_default_auth(auth: Auth) -> None:
    """Registers the ``Auth`` instance ``@role(...)``/``@permission(...)``
    use by default when not given an explicit ``get_user=``. Call once,
    typically from a service provider's ``register()``."""
    global _default_auth
    _default_auth = auth


def default_auth() -> Auth:
    if _default_auth is None:
        raise RuntimeError(
            "No default Auth configured. Call set_default_auth(auth) once, "
            "or pass get_user=... explicitly to @role()/@permission()."
        )
    return _default_auth


async def current_user(request: Request) -> Any:
    """A ``Depends(current_user)`` that resolves the default ``Auth`` (see
    :func:`set_default_auth`) fresh on every call, unlike
    ``Depends(auth.required)`` — which needs a specific, already-built
    ``Auth`` instance in hand at route-registration time. Useful in a
    controller that has no other reason to take a container-injected
    ``Auth`` (see docs/architecture/03-public-api-design.md's auth section
    for the provider-registration-order rule this sidesteps)::

        from pyforge.auth import current_user

        class ProfileController:
            async def me(self, user: Any = Depends(current_user)) -> dict:
                return {"id": user.id}
    """
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = default_auth()._user_for(token, purpose="access")
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class Policy:
    """Base class for policy objects — plain methods returning ``bool``::

        class PostPolicy(Policy):
            def update(self, user, post) -> bool:
                return user.id == post.author_id

        authorize(PostPolicy(), "update", user, post)
    """


def authorize(policy: Policy, action: str, user: Any, *args: Any, **kwargs: Any) -> None:
    """Runs ``policy.<action>(user, *args, **kwargs)``; raises
    ``HTTPException(403)`` if it returns a falsy value."""
    method = getattr(policy, action, None)
    if method is None:
        raise AttributeError(f"{type(policy).__name__} has no policy method '{action}'.")
    if not method(user, *args, **kwargs):
        raise HTTPException(status_code=403, detail="This action is unauthorized.")


def role(role_name: str, *, get_user: Callable[..., Any] | None = None) -> Callable[[Callable], Callable]:
    """Decorator: 403s unless the current user's ``.role`` equals
    ``role_name``. ``get_user`` defaults to the default ``Auth.required``
    (bearer-token) dependency — pass ``get_user=auth.session_required`` for
    cookie-session auth instead::

        class AdminController:
            @role("admin")
            async def stats(self) -> dict:
                ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        dependency = get_user or default_auth().required

        async def check(user: Any = Depends(dependency)) -> Any:
            if getattr(user, "role", None) != role_name:
                raise HTTPException(status_code=403, detail=f"Requires role '{role_name}'.")
            return user

        return inject_dependency(func, check, param_name="_pyforge_auth_check")

    return decorator


def permission(name: str, *, get_user: Callable[..., Any] | None = None) -> Callable[[Callable], Callable]:
    """Decorator: 403s unless ``user.has_permission(name)`` (a method the
    app's user model implements) returns a truthy value::

        class UserController:
            @permission("users.create")
            async def store(self, request: CreateUserRequest) -> dict:
                ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        dependency = get_user or default_auth().required

        async def check(user: Any = Depends(dependency)) -> Any:
            checker = getattr(user, "has_permission", None)
            if checker is None or not checker(name):
                raise HTTPException(status_code=403, detail=f"Requires permission '{name}'.")
            return user

        return inject_dependency(func, check, param_name="_pyforge_auth_check")

    return decorator
