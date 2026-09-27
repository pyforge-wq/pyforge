from __future__ import annotations

from pathlib import Path

from alembic.config import Config as AlembicConfig


def build_alembic_config(base_path: Path) -> AlembicConfig:
    """Builds an Alembic ``Config`` programmatically — no ``alembic.ini`` file
    needed in generated projects. The database URL isn't set here: the
    project's own ``database/migrations/env.py`` resolves it the same way
    the running application does (via ``DatabaseManager`` built from
    ``config/database.py``), so there's exactly one source of truth for it.
    """
    config = AlembicConfig()
    config.set_main_option("script_location", str(base_path / "database" / "migrations"))
    return config
