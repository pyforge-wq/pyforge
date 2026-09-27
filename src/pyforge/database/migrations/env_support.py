from __future__ import annotations

from typing import Any

from sqlalchemy import Engine


def run_migrations(engine: Engine, target_metadata: Any) -> None:
    """Called from a generated project's ``database/migrations/env.py`` to
    run migrations against a real connection ("online" mode — PyForge
    doesn't generate SQL-script/offline mode, matching the framework's
    build-for-the-common-case philosophy). Kept out of ``env.py`` itself so
    a bug fix here doesn't require regenerating every existing project's
    ``env.py``.
    """
    from alembic import context  # imported lazily: only a valid proxy during a real Alembic run

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
