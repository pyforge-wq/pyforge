from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from pyforge.config import Config

console = Console()


def register(app: typer.Typer) -> None:
    @app.command(name="queue:work")
    def queue_work(
        queue: str = typer.Option("default", "--queue", help="Comma-separated queue names, in priority order."),
        max_jobs: int | None = typer.Option(
            None, "--max-jobs", help="Stop after this many jobs (default: run forever)."
        ),
        timeout: int = typer.Option(5, "--timeout", help="Seconds to block waiting for a job each iteration."),
    ) -> None:
        """Run a worker loop against the configured queue driver. Requires
        the optional queue extra: pip install pyforge-framework[queue]
        (only needed for the redis driver — the sync driver has nothing to
        work through, since it runs jobs immediately on dispatch)."""
        cwd = Path.cwd()
        if str(cwd) not in sys.path:
            sys.path.insert(0, str(cwd))

        queue_config = Config.load_directory(cwd / "config").get("queue")
        if queue_config is None:
            console.print("[red]Error:[/red] no config/queue.py found in this project.")
            raise typer.Exit(code=1)

        from pyforge.queue import SyncQueueDriver, Worker, make_queue

        driver = make_queue(queue_config)
        if isinstance(driver, SyncQueueDriver):
            console.print(
                "[yellow]The sync queue driver runs jobs immediately on dispatch — "
                "there's nothing for a worker to pick up.[/yellow] Set QUEUE_CONNECTION=redis "
                "in .env to use a real queue."
            )
            raise typer.Exit(code=1)

        queues = [name.strip() for name in queue.split(",")]
        console.print(f"[green]Working[/green] queue(s): {', '.join(queues)}")

        def on_failure(job: object, exc: Exception) -> None:
            console.print(f"[red]Job failed:[/red] {type(job).__name__}: {exc}")

        worker = Worker(driver, on_failure=on_failure)
        processed = worker.work(queues=queues, timeout=timeout, max_jobs=max_jobs)
        console.print(f"[green]Processed {processed} job(s).[/green]")
