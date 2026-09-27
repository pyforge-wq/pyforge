from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy.orm import Session

from .manager import DatabaseManagerLike

_current_manager: ContextVar[DatabaseManagerLike | None] = ContextVar("pyforge_db_manager", default=None)
_current_session: ContextVar[Session | None] = ContextVar("pyforge_db_session", default=None)


def set_current_database(manager: DatabaseManagerLike | None) -> None:
    """Called by :class:`pyforge.core.Application` on construction, once a
    ``config/database.py`` is found. Accepts anything satisfying
    :class:`~pyforge.database.DatabaseManagerLike`, not just a literal
    ``DatabaseManager`` — see :class:`pyforge.tenancy.TenantDatabaseManager`."""
    _current_manager.set(manager)


def current_database() -> DatabaseManagerLike:
    manager = _current_manager.get()
    if manager is None:
        raise RuntimeError(
            "No database is configured. Add a config/database.py to your project "
            "(the project generator creates one by default)."
        )
    return manager


def current_session() -> Session:
    """The session for the active :func:`session_scope`. Every ``Model``
    method uses this implicitly — see docs/architecture/06-database-architecture.md."""
    session = _current_session.get()
    if session is None:
        raise RuntimeError(
            "No active database session. Model methods must run inside a "
            "`with session_scope():` block — PyForge opens one automatically "
            "around every HTTP request when config/database.py is present."
        )
    return session


@contextmanager
def session_scope(name: str | None = None) -> Iterator[Session]:
    """Open a session, commit on success, roll back on exception, always
    close. This is what wraps every HTTP request automatically, and what
    scripts/seeders/tests reach for manually outside of one."""
    manager = current_database()
    factory = manager.session_factory(name)
    session = factory()
    token = _current_session.set(session)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        _current_session.reset(token)


def get_session(name: str | None = None) -> Generator[Session, None, None]:
    """FastAPI-dependency form of :func:`session_scope`, for handlers that
    want the session injected explicitly (``Depends(get_session)``) instead
    of relying on the automatic per-request session."""
    with session_scope(name) as session:
        yield session
