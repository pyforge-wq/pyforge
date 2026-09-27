from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from pyforge.database.session import current_session

_UNSET = object()

_OPERATORS = {
    "=": operator.eq,
    "==": operator.eq,
    "!=": operator.ne,
    "<>": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "like": lambda column, value: column.like(value),
    "ilike": lambda column, value: column.ilike(value),
}

TModel = TypeVar("TModel")


@dataclass
class Paginator(Generic[TModel]):
    """The pagination envelope returned by ``QueryBuilder.paginate(...)``,
    matching the ``{"data": [...], "meta": {...}}`` shape described in the
    original spec. Turning this into an actual JSON response automatically
    is an API-resource concern (Phase 3) — for now this is a plain object
    a controller can shape however it likes, e.g. ``return paginator.__dict__``.
    """

    data: list[TModel]
    current_page: int
    per_page: int
    total: int

    @property
    def last_page(self) -> int:
        if self.per_page <= 0:
            return 1
        return max(1, -(-self.total // self.per_page))  # ceil division

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "meta": {
                "current_page": self.current_page,
                "per_page": self.per_page,
                "total": self.total,
                "last_page": self.last_page,
            },
        }


class QueryBuilder(Generic[TModel]):
    """A fluent query builder over a ``Model``, wrapping a SQLAlchemy
    ``Select`` — see docs/architecture/06-database-architecture.md. Every
    chained method mutates and returns ``self``; terminal methods
    (``get``, ``first``, ``count``, ``exists``, ``paginate``) execute the
    query against :func:`pyforge.database.current_session`.

    ``.statement`` is always the real, underlying SQLAlchemy ``Select`` —
    nothing here is inaccessible to a developer who wants to drop to raw
    SQLAlchemy for one query.
    """

    def __init__(self, model: type[TModel], *, with_trashed: bool = False) -> None:
        self.model = model
        self.statement = select(model)
        self._filters: ColumnElement[bool] | None = None
        self._with_trashed = with_trashed
        if hasattr(model, "deleted_at") and not with_trashed:
            self._filters = model.deleted_at.is_(None)  # type: ignore[attr-defined]

    def _column(self, field_name: str) -> InstrumentedAttribute[Any]:
        column = getattr(self.model, field_name, None)
        if column is None:
            raise AttributeError(f"{self.model.__name__} has no column '{field_name}'.")
        return column

    def where(self, field_name: str, op_or_value: Any, value: Any = _UNSET) -> QueryBuilder[TModel]:
        op, target = ("=", op_or_value) if value is _UNSET else (op_or_value, value)
        condition = _OPERATORS[op](self._column(field_name), target)
        self._filters = condition if self._filters is None else and_(self._filters, condition)
        return self

    def or_where(self, field_name: str, op_or_value: Any, value: Any = _UNSET) -> QueryBuilder[TModel]:
        op, target = ("=", op_or_value) if value is _UNSET else (op_or_value, value)
        condition = _OPERATORS[op](self._column(field_name), target)
        self._filters = condition if self._filters is None else or_(self._filters, condition)
        return self

    def where_in(self, field_name: str, values: list[Any]) -> QueryBuilder[TModel]:
        condition = self._column(field_name).in_(values)
        self._filters = condition if self._filters is None else and_(self._filters, condition)
        return self

    def where_null(self, field_name: str) -> QueryBuilder[TModel]:
        condition = self._column(field_name).is_(None)
        self._filters = condition if self._filters is None else and_(self._filters, condition)
        return self

    def where_not_null(self, field_name: str) -> QueryBuilder[TModel]:
        condition = self._column(field_name).is_not(None)
        self._filters = condition if self._filters is None else and_(self._filters, condition)
        return self

    def where_between(self, field_name: str, low: Any, high: Any) -> QueryBuilder[TModel]:
        condition = self._column(field_name).between(low, high)
        self._filters = condition if self._filters is None else and_(self._filters, condition)
        return self

    def order_by(self, field_name: str, direction: str = "asc") -> QueryBuilder[TModel]:
        column = self._column(field_name)
        self.statement = self.statement.order_by(column.desc() if direction == "desc" else column.asc())
        return self

    def group_by(self, *field_names: str) -> QueryBuilder[TModel]:
        self.statement = self.statement.group_by(*(self._column(name) for name in field_names))
        return self

    def having(self, condition: ColumnElement[bool]) -> QueryBuilder[TModel]:
        self.statement = self.statement.having(condition)
        return self

    def join(self, target: Any, onclause: Any = None) -> QueryBuilder[TModel]:
        self.statement = self.statement.join(target, onclause) if onclause is not None else self.statement.join(target)
        return self

    def left_join(self, target: Any, onclause: Any = None) -> QueryBuilder[TModel]:
        self.statement = self.statement.join(target, onclause, isouter=True) if onclause is not None else self.statement.join(target, isouter=True)
        return self

    def select(self, *columns: Any) -> QueryBuilder[TModel]:
        self.statement = self.statement.with_only_columns(*columns)
        return self

    def limit(self, count: int) -> QueryBuilder[TModel]:
        self.statement = self.statement.limit(count)
        return self

    def offset(self, count: int) -> QueryBuilder[TModel]:
        self.statement = self.statement.offset(count)
        return self

    def with_(self, *relationship_names: str) -> QueryBuilder[TModel]:
        """Explicit eager loading (``selectinload``) for named relationships —
        see docs/architecture/06-database-architecture.md's "no implicit
        N+1 magic" rule: this is always opt-in, never automatic."""
        self.statement = self.statement.options(
            *(selectinload(self._column(name)) for name in relationship_names)
        )
        return self

    def _final_statement(self) -> Any:
        return self.statement.where(self._filters) if self._filters is not None else self.statement

    def get(self) -> list[TModel]:
        return list(current_session().scalars(self._final_statement()).all())

    def first(self) -> TModel | None:
        return current_session().scalars(self._final_statement().limit(1)).first()

    def find(self, primary_key: Any) -> TModel | None:
        return self.where(self.model.__mapper__.primary_key[0].name, primary_key).first()  # type: ignore[attr-defined]

    def count(self) -> int:
        subquery = self._final_statement().order_by(None).subquery()
        return current_session().scalar(select(func.count()).select_from(subquery)) or 0

    def exists(self) -> bool:
        return current_session().scalar(select(self._final_statement().exists())) or False

    def paginate(self, per_page: int = 15, page: int = 1) -> Paginator[TModel]:
        total = self.count()
        page = max(1, page)
        statement = self._final_statement().limit(per_page).offset((page - 1) * per_page)
        data = list(current_session().scalars(statement).all())
        return Paginator(data=data, current_page=page, per_page=per_page, total=total)
