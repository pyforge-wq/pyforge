from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

TModel = TypeVar("TModel")


class _HybridMethod:
    """Descriptor making a method callable both on the class
    (``UserFactory.create()`` — builds a fresh, override-free instance to
    call it on) and on an instance (``UserFactory().state(role="admin").create()``
    — uses that specific instance, preserving whatever ``.state(...)`` built
    up). This is what lets both call styles from the spec work with one
    method body instead of two."""

    def __init__(self, func: Any) -> None:
        self.func = func

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is not None:
            return self.func.__get__(obj, objtype)
        assert objtype is not None
        return self.func.__get__(objtype(), objtype)


class Factory(Generic[TModel]):
    """Base class for model factories — see
    docs/architecture/06-database-architecture.md::

        class UserFactory(Factory):
            model = User

            def definition(self) -> dict:
                return {"name": "Test User", "email": f"user{uuid4()}@example.com"}

            def admin(self) -> "UserFactory":
                return self.state(role="admin")

        UserFactory.create()
        UserFactory.create_batch(10)
        UserFactory().admin().create()
        UserFactory.create(name="Override")
    """

    model: ClassVar[type[Any]]

    def __init__(self, **overrides: Any) -> None:
        self._overrides = overrides

    def definition(self) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} must implement definition().")

    def state(self, **overrides: Any) -> Factory[TModel]:
        """Return a new factory carrying additional attribute overrides —
        the building block for a subclass's own named "trait" methods."""
        return type(self)(**{**self._overrides, **overrides})

    def _attributes(self, **overrides: Any) -> dict[str, Any]:
        return {**self.definition(), **self._overrides, **overrides}

    @_HybridMethod
    def make(self, **overrides: Any) -> TModel:
        """Build an in-memory instance without persisting it."""
        return self.model(**self._attributes(**overrides))

    @_HybridMethod
    def create(self, **overrides: Any) -> TModel:
        """Build and persist an instance (via ``Model.create``)."""
        return self.model.create(**self._attributes(**overrides))

    @_HybridMethod
    def create_batch(self, count: int, **overrides: Any) -> list[TModel]:
        return [self.model.create(**self._attributes(**overrides)) for _ in range(count)]
