from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse

from pyforge.orm import ModelNotFoundError

from .exceptions import PyForgeError

if TYPE_CHECKING:
    from .application import PyForge


def register_exception_handlers(app: PyForge) -> None:
    """A consistent JSON error shape for the framework's own exceptions,
    registered automatically on every ``PyForge`` app. Application code
    can always add more via ``app.fastapi.add_exception_handler(...)`` —
    this only covers what PyForge itself raises."""
    fastapi_app = app.fastapi

    @fastapi_app.exception_handler(ModelNotFoundError)
    async def _handle_model_not_found(request: Request, exc: ModelNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @fastapi_app.exception_handler(PyForgeError)
    async def _handle_pyforge_error(request: Request, exc: PyForgeError) -> JSONResponse:
        debug = bool(app.config.get("app.debug", False))
        message = str(exc) if debug else "Internal Server Error"
        return JSONResponse(status_code=500, content={"message": message})
