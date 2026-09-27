from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pyforge.orm import Paginator


class Resource:
    """Consistent API transformation, decoupled from the ORM model shape::

        class UserResource(Resource):
            def to_dict(self, user) -> dict:
                return {"id": user.id, "name": user.name, "email": user.email}

        UserResource.make(user)             # -> dict
        UserResource.collection(users)      # -> list[dict]
        UserResource.paginated(paginator)   # -> {"data": [...], "meta": {...}}
    """

    def to_dict(self, model: Any) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} must implement to_dict().")

    @classmethod
    def make(cls, model: Any) -> dict[str, Any]:
        return cls().to_dict(model)

    @classmethod
    def collection(cls, models: Iterable[Any]) -> list[dict[str, Any]]:
        instance = cls()
        return [instance.to_dict(model) for model in models]

    @classmethod
    def paginated(cls, paginator: Paginator[Any]) -> dict[str, Any]:
        """The ``{"data": [...], "meta": {...}}`` envelope from the original
        spec, with each row transformed through this resource."""
        instance = cls()
        return {
            "data": [instance.to_dict(model) for model in paginator.data],
            "meta": {
                "current_page": paginator.current_page,
                "per_page": paginator.per_page,
                "total": paginator.total,
                "last_page": paginator.last_page,
            },
        }
