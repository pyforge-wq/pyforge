from __future__ import annotations

import subprocess
import sys

import typer
from rich.console import Console

console = Console()

_OFFICIAL_EXTRAS = {"auth", "cache", "queue", "storage"}


def register(app: typer.Typer) -> None:
    @app.command(name="package:install")
    def package_install(
        name: str = typer.Argument(
            ..., help="An official extra (auth/cache/queue/storage), or a package name."
        ),
    ) -> None:
        """A thin convenience wrapper over pip: `pyforge package:install auth`
        installs `pyforge-framework[auth]`; anything else installs
        `pyforge-<name>` (or the name as-is, if already prefixed with
        `pyforge-`) via `pip install`."""
        if name in _OFFICIAL_EXTRAS:
            target = f"pyforge-framework[{name}]"
        elif name.startswith("pyforge-"):
            target = name
        else:
            target = f"pyforge-{name}"

        console.print(f"Installing [green]{target}[/green]...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", target], check=False)
        if result.returncode != 0:
            raise typer.Exit(code=result.returncode)
        console.print(f"[green]Installed[/green] {target}.")
