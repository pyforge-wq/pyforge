from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from pyforge.database.session import current_session

from .base import Base
from .exceptions import ModelNotFoundError
from .query_builder import _UNSET, QueryBuilder
from .ulid import generate_ulid

TModel = TypeVar("TModel", bound="Model")


class Model(Base):
    """The Active-Record-style base class every application model extends —
    see docs/architecture/06-database-architecture.md and
    docs/architecture/03-public-api-design.md for the full picture::

        class User(Model):
            __tablename__ = "users"
            name: Mapped[str] = mapped_column(String(255))
            email: Mapped[str] = mapped_column(String(255), unique=True)

        User.all()
        User.find(1)
        User.where("email", "test@example.com").first()
        User.create(name="Ada", email="ada@example.com")

    Every classmethod here is a thin convenience over
    :class:`~pyforge.orm.QueryBuilder` and
    :func:`pyforge.database.current_session` — nothing is hidden: ``User.query()``
    always returns a real ``QueryBuilder`` whose ``.statement`` is a real
    SQLAlchemy ``Select``, and the current session is a real ``sqlalchemy.orm.Session``.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    @classmethod
    def query(cls: type[TModel], *, with_trashed: bool = False) -> QueryBuilder[TModel]:
        return QueryBuilder(cls, with_trashed=with_trashed)

    @classmethod
    def all(cls: type[TModel]) -> list[TModel]:
        return cls.query().get()

    @classmethod
    def find(cls: type[TModel], primary_key: Any) -> TModel | None:
        return cls.query().find(primary_key)

    @classmethod
    def find_or_fail(cls: type[TModel], primary_key: Any) -> TModel:
        instance = cls.find(primary_key)
        if instance is None:
            raise ModelNotFoundError(f"No {cls.__name__} found with primary key {primary_key!r}.")
        return instance

    @classmethod
    def where(cls: type[TModel], field_name: str, op_or_value: Any, value: Any = _UNSET) -> QueryBuilder[TModel]:
        return cls.query().where(field_name, op_or_value, value)

    @classmethod
    def create(cls: type[TModel], **attributes: Any) -> TModel:
        instance = cls(**attributes)
        session = current_session()
        session.add(instance)
        session.flush()
        return instance

    def update(self: TModel, **attributes: Any) -> TModel:
        for key, value in attributes.items():
            setattr(self, key, value)
        current_session().flush()
        return self

    def save(self: TModel) -> TModel:
        current_session().add(self)
        current_session().flush()
        return self

    def delete(self) -> None:
        session = current_session()
        if hasattr(self, "deleted_at"):
            self.deleted_at = datetime.now(timezone.utc)
            session.flush()
        else:
            session.delete(self)
            session.flush()


class UUIDModel(Model):
    """Like :class:`Model`, but with a UUID primary key instead of an
    auto-incrementing integer. A separate base class rather than a mixin —
    see docs/architecture/06-database-architecture.md's note on why the
    primary-key strategy is chosen by which base class you extend, not by
    composing mixins (SQLAlchemy declarative column overriding via mixin
    MRO is fragile; picking a base class is not)."""

    __abstract__ = True

    # Deliberately redeclares Model.id with a different type — the whole
    # point of this class (see the docstring above); mypy sees changing a
    # class attribute's type in a subclass as unsound in general, but there
    # is no ORM instance where both `Model.id` and `UUIDModel.id` are ever
    # in play together polymorphically.
    id: Mapped[str] = mapped_column(  # type: ignore[assignment]
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )


class ULIDModel(Model):
    """Like :class:`Model`, but with a ULID primary key — sortable by
    creation time, unlike a random UUID. See :func:`pyforge.orm.ulid.generate_ulid`."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(  # type: ignore[assignment]
        String(26), primary_key=True, default=generate_ulid
    )
