from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(name="serve")
    def serve(
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host."),
        port: int = typer.Option(8000, "--port", help="Bind port."),
        reload: bool = typer.Option(True, "--reload/--no-reload", help="Auto-reload on file changes."),
        app_import: str = typer.Option(
            "main:app", "--app", help="Import string for the ASGI app, as 'module:attribute'."
        ),
    ) -> None:
        """Run the development server (uvicorn) for the project in the current directory."""
        import uvicorn

        cwd = str(Path.cwd())

        console.print(f"[green]Serving[/green] {app_import} at http://{host}:{port}")
        uvicorn.run(app_import, host=host, port=port, reload=reload, app_dir=cwd)
