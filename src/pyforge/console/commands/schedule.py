from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from pyforge.config import Config

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(name="schedule:run")
    def schedule_run() -> None:
        """Runs every currently-due task from app/schedule.py's `schedule`
        object. Meant to be invoked by a real OS cron entry once a minute —
        this command itself does not loop or block. Requires the optional
        scheduler extra only if your tasks need it (the scheduler itself
        has no extra dependencies)."""
        cwd = Path.cwd()
        if str(cwd) not in sys.path:
            sys.path.insert(0, str(cwd))

        import importlib

        try:
            schedule_module = importlib.import_module("app.schedule")
            schedule = schedule_module.schedule
        except (ImportError, AttributeError) as exc:
            console.print(
                "[red]Error:[/red] couldn't import `schedule` from app/schedule.py "
                f"({exc}). Expected a module-level `schedule = Schedule()`."
            )
            raise typer.Exit(code=1) from exc

        database_config = Config.load_directory(cwd / "config").get("database")
        if database_config is not None:
            from pyforge.database import DatabaseManager, session_scope, set_current_database

            set_current_database(DatabaseManager(database_config))
            with session_scope():
                ran = schedule.run_due()
        else:
            ran = schedule.run_due()

        if ran:
            console.print(f"[green]Ran {len(ran)} scheduled task(s).[/green]")
        else:
            console.print("No tasks due.")
