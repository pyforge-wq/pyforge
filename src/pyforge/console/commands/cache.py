from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from pyforge.config import Config

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(name="cache:clear")
    def cache_clear() -> None:
        """Flush the configured cache driver. Requires the optional cache
        extra: pip install pyforge-framework[cache] (only needed for the
        redis driver)."""
        cwd = Path.cwd()
        if str(cwd) not in sys.path:
            sys.path.insert(0, str(cwd))

        cache_config = Config.load_directory(cwd / "config").get("cache")
        if cache_config is None:
            console.print("[red]Error:[/red] no config/cache.py found in this project.")
            raise typer.Exit(code=1)

        from pyforge.cache import make_cache

        make_cache(cache_config).flush()
        console.print("[green]Cache cleared.[/green]")

    @app.command(name="config:clear")
    def config_clear() -> None:
        """Clear cached bytecode for config/*.py so the next run re-reads
        them from disk. PyForge doesn't cache parsed config across
        processes today (each Config.load_directory() call already re-reads
        the files), so this only clears Python's own __pycache__ for
        config/ — mainly useful after editing a config file and seeing
        stale behavior from a stray .pyc."""
        cwd = Path.cwd()
        cache_dir = cwd / "config" / "__pycache__"
        removed = 0
        if cache_dir.is_dir():
            for file in cache_dir.glob("*.pyc"):
                file.unlink()
                removed += 1
        console.print(f"[green]Cleared[/green] {removed} cached config file(s).")
