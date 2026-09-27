from __future__ import annotations

import typer
from rich.console import Console

from pyforge.console.commands import (
    cache,
    db,
    make,
    migrate,
    new,
    package,
    queue,
    route_list,
    schedule,
    serve,
)

console = Console()

app = typer.Typer(
    name="pyforge",
    help="PyForge: a batteries-included web framework for Python, built on FastAPI.",
    no_args_is_help=True,
)

_BUILTIN_COMMAND_MODULES = (new, serve, route_list, make, migrate, db, cache, queue, schedule, package)

for _module in _BUILTIN_COMMAND_MODULES:
    _module.register(app)


def _load_package_commands() -> None:
    """Discover third-party command registrations via the ``pyforge.commands``
    entry-point group, so packages (``pyforge-auth``, ``pyforge-tenancy``, ...)
    can add their own ``pyforge`` subcommands without touching this file.

    A package opts in from its own ``pyproject.toml``::

        [project.entry-points."pyforge.commands"]
        auth = "pyforge_auth.commands:register"

    where ``register(app: typer.Typer) -> None`` adds its subcommands.
    """
    from importlib.metadata import entry_points

    discovered = entry_points(group="pyforge.commands")

    for entry_point in discovered:
        try:
            register_fn = entry_point.load()
            register_fn(app)
        except Exception as exc:  # noqa: BLE001 - a broken plugin shouldn't break the whole CLI
            console.print(
                f"[yellow]Warning:[/yellow] failed to load command package '{entry_point.name}': {exc}"
            )


_load_package_commands()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
