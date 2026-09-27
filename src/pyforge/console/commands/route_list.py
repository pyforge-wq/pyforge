from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(name="route:list")
    def route_list(
        app_import: str = typer.Option(
            "main:app", "--app", help="Import string for the PyForge/FastAPI app, as 'module:attribute'."
        ),
    ) -> None:
        """List every registered route in the project's application.

        Reads the app's generated OpenAPI schema rather than walking FastAPI's
        internal route tree, since that keeps this command correct across
        FastAPI versions and regardless of how deeply routers are nested.
        """
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        module_name, _, attr = app_import.partition(":")
        if not attr:
            console.print("[red]Error:[/red] --app must look like 'module:attribute', e.g. 'main:app'.")
            raise typer.Exit(code=1)

        try:
            import importlib

            module = importlib.import_module(module_name)
            target = getattr(module, attr)
        except (ImportError, AttributeError) as exc:
            console.print(f"[red]Error importing '{app_import}':[/red] {exc}")
            raise typer.Exit(code=1) from exc

        fastapi_app = getattr(target, "fastapi", target)
        schema = fastapi_app.openapi()

        table = Table(title="Routes")
        table.add_column("Method(s)")
        table.add_column("Path")

        for path in sorted(schema.get("paths", {})):
            methods = ",".join(sorted(m.upper() for m in schema["paths"][path]))
            table.add_row(methods, path)

        console.print(table)
