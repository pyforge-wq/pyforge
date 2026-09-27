from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class TimestampsMixin:
    """Adds ``created_at``/``updated_at`` columns, kept in sync by SQLAlchemy
    itself (a client-side default and ``onupdate``, evaluated on flush) —
    never something application code has to remember to set.

    Mix in alongside :class:`~pyforge.orm.Model`, e.g.::

        class Post(TimestampsMixin, Model):
            __tablename__ = "posts"
    """

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SoftDeletesMixin:
    """Adds a nullable ``deleted_at`` column. Any model with this mixin gets
    two behavior changes, applied by :class:`~pyforge.orm.Model` and
    :class:`~pyforge.orm.QueryBuilder` whenever they see a ``deleted_at``
    attribute on the model:

    - Every query built through ``Model.query()``/``where()``/``all()``
      excludes soft-deleted rows by default (``deleted_at IS NULL``), unless
      built with ``Model.query(with_trashed=True)``.
    - ``instance.delete()`` sets ``deleted_at`` to now instead of issuing a
      ``DELETE``.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True)
