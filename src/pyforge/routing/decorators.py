from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from fastapi import Depends


def inject_dependency(
    func: Callable[..., Any], dependency: Callable[..., Any], *, param_name: str = "_pyforge_injected"
) -> Callable[..., Any]:
    """Appends a keyword-only parameter with a ``Depends(dependency)``
    default to ``func``'s signature, so FastAPI resolves (and can reject via
    an exception) it before the handler body runs, then strips it back out
    before calling the real function.

    This is the building block behind decorators that need to run a check
    before a route handler without changing its signature from the caller's
    perspective — ``pyforge.auth``'s ``@role``/``@permission`` and
    ``pyforge.security``'s ``@rate_limit`` are both built on this. It's the
    same signature-rewriting technique :class:`~pyforge.routing.Router` uses
    for controller actions and ``FormRequest`` injection, generalized into a
    reusable core utility so unrelated optional packages don't each
    reimplement it (or depend on each other to share it).
    """
    signature = inspect.signature(func)
    new_param = inspect.Parameter(
        param_name, inspect.Parameter.KEYWORD_ONLY, default=Depends(dependency), annotation=Any
    )
    new_signature = signature.replace(parameters=[*signature.parameters.values(), new_param])

    if inspect.iscoroutinefunction(func):

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop(param_name, None)
            return await func(*args, **kwargs)

    else:

        def wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            kwargs.pop(param_name, None)
            return func(*args, **kwargs)

    wrapper.__signature__ = new_signature  # type: ignore[attr-defined]
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__qualname__ = func.__qualname__
    wrapper.__module__ = func.__module__
    return wrapper
