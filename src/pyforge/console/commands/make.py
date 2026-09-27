from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from pyforge.console.generator import write_stub
from pyforge.console.naming import (
    class_name_with_suffix,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
)

console = Console()


def _generate(stub: str, target: Path, context: dict) -> None:
    try:
        write_stub(stub, target, context)
    except FileExistsError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Created[/green] {target}")


def register(app: typer.Typer) -> None:
    @app.command(name="make:controller")
    def make_controller(name: str = typer.Argument(..., help="e.g. 'User' or 'UserController'.")) -> None:
        """Generate a new controller in app/controllers/."""
        class_name = class_name_with_suffix(name, "Controller")
        target = Path.cwd() / "app" / "controllers" / f"{to_snake_case(class_name)}.py"
        _generate(
            "controller.py.stub",
            target,
            {"class_name": class_name, "resource_kebab": to_kebab_case(name.removesuffix("Controller"))},
        )

    @app.command(name="make:middleware")
    def make_middleware(name: str = typer.Argument(..., help="e.g. 'Auth' or 'EnsureIsAdmin'.")) -> None:
        """Generate a new middleware dependency in app/middleware/."""
        function_name = to_snake_case(name)
        target = Path.cwd() / "app" / "middleware" / f"{function_name}.py"
        _generate(
            "middleware.py.stub",
            target,
            {"function_name": function_name, "middleware_name": to_kebab_case(name)},
        )

    @app.command(name="make:provider")
    def make_provider(name: str = typer.Argument(..., help="e.g. 'Payment' or 'PaymentServiceProvider'.")) -> None:
        """Generate a new service provider in app/providers/."""
        class_name = class_name_with_suffix(name, "ServiceProvider")
        target = Path.cwd() / "app" / "providers" / f"{to_snake_case(class_name)}.py"
        _generate("provider.py.stub", target, {"class_name": class_name})

    @app.command(name="make:command")
    def make_command(name: str = typer.Argument(..., help="e.g. 'ImportUsers'.")) -> None:
        """Generate a new console command class in app/commands/."""
        class_name = to_pascal_case(name)
        target = Path.cwd() / "app" / "commands" / f"{to_snake_case(class_name)}.py"
        _generate("command.py.stub", target, {"class_name": class_name})

    @app.command(name="make:model")
    def make_model(
        name: str = typer.Argument(..., help="e.g. 'User'."),
        migration: bool = typer.Option(
            False, "--migration", "-m", help="Also create a matching 'create_<table>_table' migration."
        ),
    ) -> None:
        """Generate a new model in app/models/. Table name is naively pluralized
        (User -> users); rename __tablename__ yourself for irregular plurals."""
        class_name = to_pascal_case(name)
        table_name = f"{to_snake_case(class_name)}s"
        target = Path.cwd() / "app" / "models" / f"{to_snake_case(class_name)}.py"
        _generate("model.py.stub", target, {"class_name": class_name, "table_name": table_name})

        if migration:
            from alembic import command as alembic_command

            from pyforge.database.migrations import build_alembic_config

            cfg = build_alembic_config(Path.cwd())
            script = alembic_command.revision(cfg, message=f"create_{table_name}_table", autogenerate=False)
            if script is not None and not isinstance(script, list):
                console.print(f"[green]Created[/green] {script.path}")

    @app.command(name="make:schema")
    def make_schema(name: str = typer.Argument(..., help="e.g. 'User' or 'UserSchema'.")) -> None:
        """Generate a native Pydantic model in app/schemas/."""
        class_name = class_name_with_suffix(name, "Schema")
        target = Path.cwd() / "app" / "schemas" / f"{to_snake_case(class_name)}.py"
        _generate("schema.py.stub", target, {"class_name": class_name})

    @app.command(name="make:request")
    def make_request(name: str = typer.Argument(..., help="e.g. 'CreateUser' or 'CreateUserRequest'.")) -> None:
        """Generate a FormRequest (string-rule validation) in app/requests/."""
        class_name = class_name_with_suffix(name, "Request")
        target = Path.cwd() / "app" / "requests" / f"{to_snake_case(class_name)}.py"
        _generate("request.py.stub", target, {"class_name": class_name})

    @app.command(name="make:resource")
    def make_resource(name: str = typer.Argument(..., help="e.g. 'User' or 'UserResource'.")) -> None:
        """Generate an API resource transformer in app/resources/."""
        class_name = class_name_with_suffix(name, "Resource")
        target = Path.cwd() / "app" / "resources" / f"{to_snake_case(class_name)}.py"
        _generate("resource.py.stub", target, {"class_name": class_name})

    @app.command(name="make:policy")
    def make_policy(name: str = typer.Argument(..., help="e.g. 'Post' or 'PostPolicy'.")) -> None:
        """Generate an authorization policy in app/policies/. Requires the
        optional auth extra: pip install pyforge-framework[auth]."""
        class_name = class_name_with_suffix(name, "Policy")
        target = Path.cwd() / "app" / "policies" / f"{to_snake_case(class_name)}.py"
        _generate("policy.py.stub", target, {"class_name": class_name})

    @app.command(name="make:job")
    def make_job(name: str = typer.Argument(..., help="e.g. 'SendWelcomeEmail'.")) -> None:
        """Generate a queued job in app/jobs/. Requires the optional queue
        extra: pip install pyforge-framework[queue] (only for the redis driver)."""
        class_name = to_pascal_case(name)
        target = Path.cwd() / "app" / "jobs" / f"{to_snake_case(class_name)}.py"
        _generate("job.py.stub", target, {"class_name": class_name})

    @app.command(name="make:event")
    def make_event(name: str = typer.Argument(..., help="e.g. 'UserRegistered'.")) -> None:
        """Generate an event class in app/events/."""
        class_name = to_pascal_case(name)
        target = Path.cwd() / "app" / "events" / f"{to_snake_case(class_name)}.py"
        _generate("event.py.stub", target, {"class_name": class_name})

    @app.command(name="make:listener")
    def make_listener(name: str = typer.Argument(..., help="e.g. 'SendWelcomeEmail'.")) -> None:
        """Generate an event listener in app/listeners/."""
        class_name = to_pascal_case(name)
        target = Path.cwd() / "app" / "listeners" / f"{to_snake_case(class_name)}.py"
        _generate("listener.py.stub", target, {"class_name": class_name})

    @app.command(name="make:notification")
    def make_notification(name: str = typer.Argument(..., help="e.g. 'WelcomeNotification'.")) -> None:
        """Generate a notification in app/notifications/."""
        class_name = to_pascal_case(name)
        target = Path.cwd() / "app" / "notifications" / f"{to_snake_case(class_name)}.py"
        _generate("notification.py.stub", target, {"class_name": class_name})
