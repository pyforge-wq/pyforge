from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from pyforge.database import DatabaseManager

from .context import current_tenant_id


class TenantDatabaseManager:
    """Database-per-tenant: routes to a distinct :class:`~pyforge.database.DatabaseManager`
    per tenant, built lazily from ``connection_for_tenant(tenant_id)``.
    Duck-types :class:`~pyforge.database.DatabaseManager`'s ``engine``/
    ``session_factory``/``dispose`` interface, so it's a drop-in replacement
    passed straight to ``set_current_database(...)`` — everything downstream
    (``session_scope()``, ``Model``) works unmodified::

        def connection_for_tenant(tenant_id: str) -> dict:
            return {"driver": "mysql", "database": f"tenant_{tenant_id}", ...}

        set_current_database(TenantDatabaseManager(connection_for_tenant=connection_for_tenant))
    """

    def __init__(self, *, connection_for_tenant: Callable[[Any], dict[str, Any]]) -> None:
        self._connection_for_tenant = connection_for_tenant
        self._managers: dict[Any, DatabaseManager] = {}

    def _manager_for(self, tenant_id: Any) -> DatabaseManager:
        if tenant_id not in self._managers:
            connection = self._connection_for_tenant(tenant_id)
            self._managers[tenant_id] = DatabaseManager({"default": "tenant", "connections": {"tenant": connection}})
        return self._managers[tenant_id]

    def _resolve(self, name: str | None) -> DatabaseManager:
        tenant_id = name if name is not None else current_tenant_id()
        return self._manager_for(tenant_id)

    def engine(self, name: str | None = None) -> Engine:
        return self._resolve(name).engine()

    def session_factory(self, name: str | None = None) -> sessionmaker[Session]:
        return self._resolve(name).session_factory()

    def dispose(self) -> None:
        for manager in self._managers.values():
            manager.dispose()
        self._managers.clear()
