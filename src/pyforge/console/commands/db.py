from __future__ import annotations

import importlib
import sys
from pathlib import Path

import typer
from rich.console import Console

from pyforge.config import Config
from pyforge.database import DatabaseManager, session_scope, set_current_database

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(name="db:seed")
    def db_seed(
        seeder: str = typer.Option(
            "database.seeders.database_seeder.DatabaseSeeder",
            "--class",
            help="Dotted path to the seeder class to run.",
        ),
    ) -> None:
        """Run a seeder (defaults to database.seeders.database_seeder.DatabaseSeeder)."""
        cwd = Path.cwd()
        if str(cwd) not in sys.path:
            sys.path.insert(0, str(cwd))

        config = Config.load_directory(cwd / "config")
        database_config = config.get("database")
        if database_config is None:
            console.print("[red]Error:[/red] no config/database.py found in this project.")
            raise typer.Exit(code=1)

        set_current_database(DatabaseManager(database_config))

        module_path, _, class_name = seeder.rpartition(".")
        try:
            module = importlib.import_module(module_path)
            seeder_class = getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            console.print(f"[red]Error importing seeder '{seeder}':[/red] {exc}")
            raise typer.Exit(code=1) from exc

        with session_scope():
            seeder_class().run()

        console.print(f"[green]Seeded[/green] using {seeder}")
