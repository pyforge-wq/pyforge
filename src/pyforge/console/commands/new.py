from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from pyforge.console.generator import scaffold_project

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(name="new")
    def new(
        name: str = typer.Argument(..., help="Project directory to create, e.g. 'blog'."),
        path: str | None = typer.Option(None, "--path", help="Parent directory (defaults to cwd)."),
    ) -> None:
        """Create a new PyForge project in a fresh directory named NAME."""
        parent = Path(path) if path else Path.cwd()
        destination = parent / name
        try:
            scaffold_project(destination, project_name=name)
        except FileExistsError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[green]Created[/green] {destination}")
        console.print("\nNext steps:\n")
        console.print(f"  cd {name}")
        console.print("  pip install -e .  # or: pip install pyforge-framework")
        console.print("  pyforge serve")

    @app.command(name="init")
    def init(
        name: str | None = typer.Argument(
            None, help="Project name (defaults to the current directory's name)."
        ),
    ) -> None:
        """Scaffold a PyForge project into the CURRENT directory."""
        destination = Path.cwd()
        project_name = name or destination.name
        try:
            scaffold_project(destination, project_name=project_name)
        except FileExistsError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[green]Initialized[/green] {project_name} in {destination}")
        console.print("\nNext steps:\n")
        console.print("  pip install -e .  # or: pip install pyforge-framework")
        console.print("  pyforge serve")
