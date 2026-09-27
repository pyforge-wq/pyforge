from __future__ import annotations

import sys
from pathlib import Path

import typer
from alembic import command
from rich.console import Console

from pyforge.database.migrations import build_alembic_config

console = Console()


def _cwd_on_path() -> Path:
    cwd = Path.cwd()
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))
    return cwd


def register(app: typer.Typer) -> None:
    @app.command(name="migrate")
    def migrate() -> None:
        """Run every pending migration."""
        cfg = build_alembic_config(_cwd_on_path())
        command.upgrade(cfg, "head")

    @app.command(name="migrate:make")
    def migrate_make(name: str = typer.Argument(..., help="e.g. 'create_users_table'.")) -> None:
        """Create a new, timestamped migration file in database/migrations/versions/."""
        cfg = build_alembic_config(_cwd_on_path())
        script = command.revision(cfg, message=name, autogenerate=False)
        if script is not None and not isinstance(script, list):
            console.print(f"[green]Created[/green] {script.path}")

    @app.command(name="make:migration")
    def make_migration(name: str = typer.Argument(..., help="e.g. 'create_users_table'.")) -> None:
        """Alias for migrate:make."""
        migrate_make(name)

    @app.command(name="migrate:rollback")
    def migrate_rollback(step: int = typer.Option(1, "--step", help="Number of migrations to roll back.")) -> None:
        """Roll back the last (or last N) migration(s)."""
        cfg = build_alembic_config(_cwd_on_path())
        command.downgrade(cfg, f"-{step}")

    @app.command(name="migrate:status")
    def migrate_status() -> None:
        """Show the current migration and full migration history."""
        cfg = build_alembic_config(_cwd_on_path())
        console.print("[bold]Current revision:[/bold]")
        command.current(cfg, verbose=True)
        console.print("\n[bold]History:[/bold]")
        command.history(cfg, indicate_current=True)
