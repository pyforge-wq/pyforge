from __future__ import annotations

from typing import Any

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from pyforge.orm import QueryBuilder

from .context import current_tenant_id_or_none


class TenantScopedMixin:
    """Shared-database, ``tenant_id``-column multi-tenancy — mix in
    alongside :class:`~pyforge.orm.Model`::

        class Post(TenantScopedMixin, Model):
            __tablename__ = "posts"
            title: Mapped[str] = mapped_column(String(255))

    Every read (`all`, `find`, `where`, `query`) is scoped to
    ``current_tenant_id()`` automatically, and `create` stamps it in — this
    is the "prevent accidental cross-tenant queries" guarantee: a developer
    would have to go out of their way (``query(with_trashed=...)``-style,
    there is no such escape hatch here on purpose) to see another tenant's
    rows through this model. Needs a real ``tenant_id`` for the *type* your
    app uses for tenant ids — override this column yourself if it isn't a
    plain integer.

    ``create()`` always **overwrites** a caller-supplied ``tenant_id`` with
    the current tenant rather than only filling it in when absent —
    deliberately, not just as a convenience: ``Model.create(**attributes)``
    has no mass-assignment protection (there's no
    ``$fillable``/``$guarded``-style allowlist here — see docs/architecture/03-public-api-design.md's
    security notes), so a controller that does something like
    ``Post.create(**request.validated())`` must not be able to leak a
    `tenant_id` from request data into cross-tenant writes, even by accident.
    """

    tenant_id: Mapped[int] = mapped_column(Integer, index=True)

    @classmethod
    def query(cls, *, with_trashed: bool = False) -> QueryBuilder[Any]:
        builder = super().query(with_trashed=with_trashed)  # type: ignore[misc]
        tenant_id = current_tenant_id_or_none()
        if tenant_id is not None:
            builder = builder.where("tenant_id", tenant_id)
        return builder

    @classmethod
    def create(cls, **attributes: Any) -> Any:
        attributes.pop("tenant_id", None)
        tenant_id = current_tenant_id_or_none()
        if tenant_id is not None:
            attributes["tenant_id"] = tenant_id
        return super().create(**attributes)  # type: ignore[misc]
