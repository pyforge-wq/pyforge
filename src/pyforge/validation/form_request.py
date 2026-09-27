from __future__ import annotations

from typing import Any, ClassVar

from fastapi import HTTPException, Request

from .rules import validate


class FormRequest:
    """Pipe-separated-rule request validation, as an alternative to a native
    Pydantic model — both work as a controller parameter type::

        class CreateUserRequest(FormRequest):
            rules = {
                "name": "required|string|max:255",
                "email": "required|email|unique:users",
                "password": "required|min:8",
            }

        class UserController:
            async def store(self, request: CreateUserRequest) -> dict:
                data = request.validated()
                ...

    A parameter annotated with a ``FormRequest`` subclass is detected and
    turned into a FastAPI dependency automatically by
    :class:`pyforge.routing.Router` — no ``Depends(...)`` needed. On failure,
    raises ``HTTPException(422, detail={"errors": {...}})`` before the
    controller method ever runs, matching FastAPI's own validation-error
    shape convention (a dict of field -> messages).
    """

    rules: ClassVar[dict[str, str]] = {}

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        errors = validate(data, self.rules)
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})
        self._validated = {field: data[field] for field in self.rules if field in data}

    def validated(self) -> dict[str, Any]:
        return dict(self._validated)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._validated[name]
        except KeyError:
            raise AttributeError(name) from None

    @classmethod
    async def _as_dependency(cls, request: Request) -> FormRequest:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - any malformed-body error becomes a 422, not a 500
            body = {}
        if not isinstance(body, dict):
            body = {}
        return cls(body)
