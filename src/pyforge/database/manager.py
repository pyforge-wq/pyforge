from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@runtime_checkable
class DatabaseManagerLike(Protocol):
    """The structural contract :func:`pyforge.database.set_current_database`
    actually needs — satisfied by :class:`DatabaseManager` itself, and by
    anything else that resolves an ``Engine``/``sessionmaker`` per named
    connection, e.g. :class:`pyforge.tenancy.TenantDatabaseManager` (database-
    per-tenant). Kept here, in core, so an optional package can plug into
    ``session_scope()``/``Model`` without core ever importing that package."""

    def engine(self, name: str | None = None) -> Engine: ...

    def session_factory(self, name: str | None = None) -> sessionmaker[Session]: ...

    def dispose(self) -> None: ...


class DatabaseManager:
    """Builds and caches a SQLAlchemy :class:`Engine` and session factory per
    named connection, from the same ``config/database.py`` shape used
    throughout the rest of the config system::

        config = {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": "storage/database.sqlite"},
                "mysql": {"driver": "mysql", "host": ..., "port": ..., ...},
            },
        }

    PyForge uses plain, synchronous SQLAlchemy for the ORM layer — see
    docs/architecture/06-database-architecture.md for why (it matches the
    framework's Eloquent-style ``Model`` API, and keeps the Alembic
    migration story simple and reliable). A synchronous call from an
    ``async def`` controller briefly blocks the event loop; for
    high-concurrency code paths, use a real ``sqlalchemy.ext.asyncio``
    session directly instead — nothing here prevents that.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._engines: dict[str, Engine] = {}
        self._session_factories: dict[str, sessionmaker[Session]] = {}

    def _resolve_name(self, name: str | None) -> str:
        resolved = name or self._config.get("default")
        if not isinstance(resolved, str):
            raise KeyError("config/database.py must set a string 'default' connection name.")
        return resolved

    def _connection_config(self, name: str | None) -> dict[str, Any]:
        resolved = self._resolve_name(name)
        connections = self._config.get("connections", {})
        if resolved not in connections:
            raise KeyError(
                f"No database connection named '{resolved}' in config/database.py's 'connections'."
            )
        return connections[resolved]

    def connection_url(self, name: str | None = None) -> str:
        conn = self._connection_config(name)
        driver = conn.get("driver", "sqlite")

        if driver == "sqlite":
            return f"sqlite:///{conn['database']}"

        if driver == "mysql":
            user = quote_plus(str(conn.get("username", "root")))
            password = quote_plus(str(conn.get("password", "")))
            host = conn.get("host", "127.0.0.1")
            port = conn.get("port", 3306)
            database = conn["database"]
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

        if driver == "postgresql":
            user = quote_plus(str(conn.get("username", "postgres")))
            password = quote_plus(str(conn.get("password", "")))
            host = conn.get("host", "127.0.0.1")
            port = conn.get("port", 5432)
            database = conn["database"]
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

        raise ValueError(f"Unknown database driver '{driver}'.")

    def engine(self, name: str | None = None) -> Engine:
        key = self._resolve_name(name)
        if key not in self._engines:
            connect_args = {"check_same_thread": False} if self.connection_url(name).startswith("sqlite") else {}
            self._engines[key] = create_engine(self.connection_url(name), connect_args=connect_args)
        return self._engines[key]

    def session_factory(self, name: str | None = None) -> sessionmaker[Session]:
        key = self._resolve_name(name)
        if key not in self._session_factories:
            self._session_factories[key] = sessionmaker(bind=self.engine(name), expire_on_commit=False)
        return self._session_factories[key]

    def dispose(self) -> None:
        """Close all cached engines' connection pools. Mainly useful in tests."""
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()
        self._session_factories.clear()
