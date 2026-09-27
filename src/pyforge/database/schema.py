from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from alembic import op


@dataclass
class _DropColumn:
    name: str


def _server_default_for(value: Any) -> Any:
    """Migrations are pure DDL — a plain SQLAlchemy ``Column(default=...)``
    (a client-side, Python-level default) would silently do nothing for any
    row inserted outside the exact SQLAlchemy Core ``Table`` object the
    migration builds and discards, which is every real insert. A migration's
    ``.default(value)`` has to become a real ``server_default`` instead, so
    it actually reaches the database — this converts common Python literals
    into one; a SQLAlchemy expression (``sa.func.now()``, ``sa.text(...)``)
    is passed through unchanged."""
    if isinstance(value, sa.sql.ClauseElement):
        return value
    if isinstance(value, bool):
        return sa.true() if value else sa.false()
    if isinstance(value, (int, float)):
        return sa.text(str(value))
    if isinstance(value, str):
        return sa.text("'" + value.replace("'", "''") + "'")
    raise TypeError(
        f"Unsupported default value type {type(value)!r} — pass a SQLAlchemy "
        "expression (e.g. sa.func.now()) for anything beyond bool/int/float/str."
    )


class Column:
    """A pending column spec built up by chaining, e.g.
    ``table.string("email").unique()`` — converted to a real
    ``sqlalchemy.Column`` only when the enclosing ``Schema.create``/``Schema.table``
    block applies it, via :meth:`to_sqlalchemy`."""

    def __init__(self, name: str, type_: Any) -> None:
        self.name = name
        self.type_ = type_
        self._nullable = True
        self._unique = False
        self._default: Any = None
        self._foreign_key: str | None = None
        self._primary_key = False

    def nullable(self, value: bool = True) -> Column:
        self._nullable = value
        return self

    def unique(self) -> Column:
        self._unique = True
        return self

    def default(self, value: Any) -> Column:
        self._default = value
        return self

    def primary_key(self) -> Column:
        self._primary_key = True
        self._nullable = False
        return self

    def references(self, table: str, column: str = "id") -> Column:
        self._foreign_key = f"{table}.{column}"
        return self

    def to_sqlalchemy(self) -> sa.Column:
        args: list[Any] = [self.name, self.type_]
        if self._foreign_key:
            args.append(sa.ForeignKey(self._foreign_key))
        kwargs: dict[str, Any] = {"nullable": self._nullable, "primary_key": self._primary_key}
        if self._unique:
            kwargs["unique"] = True
        if self._default is not None:
            kwargs["server_default"] = _server_default_for(self._default)
        return sa.Column(*args, **kwargs)


class TableBuilder:
    """Yielded by ``Schema.create(name)``/``Schema.table(name)`` inside a
    migration's ``upgrade()``. See docs/architecture/06-database-architecture.md."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._pending: list[Column] = []
        self._drops: list[_DropColumn] = []

    def id(self) -> TableBuilder:
        self._pending.append(Column("id", sa.Integer).primary_key())
        return self

    def string(self, name: str, length: int = 255) -> Column:
        column = Column(name, sa.String(length))
        self._pending.append(column)
        return column

    def text(self, name: str) -> Column:
        column = Column(name, sa.Text)
        self._pending.append(column)
        return column

    def integer(self, name: str) -> Column:
        column = Column(name, sa.Integer)
        self._pending.append(column)
        return column

    def big_integer(self, name: str) -> Column:
        column = Column(name, sa.BigInteger)
        self._pending.append(column)
        return column

    def boolean(self, name: str) -> Column:
        column = Column(name, sa.Boolean)
        self._pending.append(column)
        return column

    def float(self, name: str) -> Column:
        column = Column(name, sa.Float)
        self._pending.append(column)
        return column

    def date(self, name: str) -> Column:
        column = Column(name, sa.Date)
        self._pending.append(column)
        return column

    def datetime(self, name: str) -> Column:
        column = Column(name, sa.DateTime)
        self._pending.append(column)
        return column

    def json(self, name: str) -> Column:
        column = Column(name, sa.JSON)
        self._pending.append(column)
        return column

    def foreign_id(self, name: str) -> Column:
        """Shorthand for an integer column meant for ``.references(...)``,
        e.g. ``table.foreign_id("author_id").references("authors")``."""
        column = Column(name, sa.Integer)
        self._pending.append(column)
        return column

    def timestamps(self) -> TableBuilder:
        """Adds nullable ``created_at``/``updated_at`` columns — nullable
        because *populating* them is the ORM's job
        (:class:`pyforge.orm.TimestampsMixin`), not the schema's; a NOT NULL
        constraint here would reject any insert that mixin didn't touch
        (raw SQL, a seeder using a plain connection, ...)."""
        self._pending.append(Column("created_at", sa.DateTime).nullable(True))
        self._pending.append(Column("updated_at", sa.DateTime).nullable(True))
        return self

    def soft_deletes(self) -> TableBuilder:
        self._pending.append(Column("deleted_at", sa.DateTime).nullable(True))
        return self

    def drop_column(self, name: str) -> TableBuilder:
        self._drops.append(_DropColumn(name))
        return self

    def built_columns(self) -> list[sa.Column]:
        return [column.to_sqlalchemy() for column in self._pending]


class Schema:
    """The migration-time schema builder — a thin, readable layer over
    Alembic's ``op.*`` operations. Used inside a migration file's
    ``upgrade()``/``downgrade()``::

        def upgrade() -> None:
            with Schema.create("users") as table:
                table.id()
                table.string("name")
                table.string("email").unique()
                table.timestamps()

        def downgrade() -> None:
            Schema.drop("users")
    """

    @staticmethod
    @contextmanager
    def create(name: str) -> Iterator[TableBuilder]:
        builder = TableBuilder(name)
        yield builder
        op.create_table(name, *builder.built_columns())

    @staticmethod
    def drop(name: str) -> None:
        op.drop_table(name)

    @staticmethod
    @contextmanager
    def table(name: str) -> Iterator[TableBuilder]:
        """For ALTER-TABLE-style migrations: add or drop columns on an
        existing table."""
        builder = TableBuilder(name)
        yield builder
        for column in builder.built_columns():
            op.add_column(name, column)
        for drop in builder._drops:
            op.drop_column(name, drop.name)
