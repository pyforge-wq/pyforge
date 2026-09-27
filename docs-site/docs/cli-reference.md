# CLI Reference

The `pyforge` CLI is built on [Typer](https://typer.tiangolo.com/). Run
`pyforge --help` or `pyforge <command> --help` for live usage — this page is
a task-oriented reference.

## Project setup

| Command | What it does |
|---|---|
| `pyforge new NAME [--path PATH]` | Scaffolds a new project directory `NAME` (under `PATH`, default: cwd). Fails if the target already exists and is non-empty. |
| `pyforge init [NAME]` | Same scaffolding, into the **current** directory. `NAME` is only used for `{{ project_name }}` substitutions. Fails if the current directory is non-empty. |
| `pyforge serve [--host] [--port] [--reload/--no-reload] [--app MODULE:ATTR]` | Runs the project with uvicorn. Defaults: `127.0.0.1:8000`, reload on, `main:app`. |
| `pyforge route:list [--app MODULE:ATTR]` | Prints every route (method + path) from the app's OpenAPI schema. |

## Code generators (`make:*`)

| Command | Generates |
|---|---|
| `pyforge make:controller NAME` | `app/controllers/<snake_case>.py`, a `<PascalCase>Controller` class |
| `pyforge make:middleware NAME` | `app/middleware/<snake_case>.py`, an async FastAPI-dependency function |
| `pyforge make:provider NAME` | `app/providers/<snake_case>.py`, a `<PascalCase>ServiceProvider` |
| `pyforge make:command NAME` | `app/commands/<snake_case>.py` — not yet auto-discovered/runnable, see [Troubleshooting](troubleshooting.md) |
| `pyforge make:model NAME [--migration/-m]` | `app/models/<snake_case>.py`; with `--migration`, also a matching `create_<table>_table` migration |
| `pyforge make:migration NAME` (alias `migrate:make`) | A new, timestamped migration under `database/migrations/versions/` |
| `pyforge make:schema NAME` | `app/schemas/<snake_case>.py`, a native Pydantic `BaseModel` |
| `pyforge make:request NAME` | `app/requests/<snake_case>.py`, a `FormRequest` subclass |
| `pyforge make:resource NAME` | `app/resources/<snake_case>.py`, a `Resource` subclass |
| `pyforge make:policy NAME` | `app/policies/<snake_case>.py`, a `Policy` subclass (needs `[auth]`) |
| `pyforge make:job NAME` | `app/jobs/<snake_case>.py`, a `Job` subclass |
| `pyforge make:event NAME` | `app/events/<snake_case>.py`, a plain event class |
| `pyforge make:listener NAME` | `app/listeners/<snake_case>.py`, a `Listener` subclass |
| `pyforge make:notification NAME` | `app/notifications/<snake_case>.py`, a `Notification` subclass |

Every `make:*` command adds the appropriate class suffix automatically if
you omit it (`pyforge make:controller User` and
`pyforge make:controller UserController` both produce `UserController`).

## Database

| Command | What it does |
|---|---|
| `pyforge migrate` | Runs every pending migration |
| `pyforge migrate:rollback [--step N]` | Rolls back the last `N` migrations (default 1) |
| `pyforge migrate:status` | Prints current revision + full history |
| `pyforge db:seed [--class DOTTED.PATH]` | Runs a seeder's `run()`, default `database.seeders.database_seeder.DatabaseSeeder` |

## Cache, queue, scheduler

| Command | What it does |
|---|---|
| `pyforge cache:clear` | Flushes the configured cache driver |
| `pyforge config:clear` | Clears `config/__pycache__`'s compiled bytecode |
| `pyforge queue:work [--queue NAMES] [--max-jobs N] [--timeout SECONDS]` | Runs a worker loop; refuses to run against the sync driver |
| `pyforge schedule:run` | Runs every currently-due task from `app/schedule.py` once, then exits — meant for a real cron entry |

## Packages

| Command | What it does |
|---|---|
| `pyforge package:install NAME` | An official extra (`auth`/`cache`/`queue`/`storage`) installs `pyforge-framework[NAME]`; anything else installs `pyforge-NAME` |

## Generated project layout

```
myapp/
├── app/
│   ├── controllers/        welcome_controller.py (demo) + your controllers
│   ├── models/  schemas/  services/  repositories/
│   ├── middleware/  requests/  resources/  policies/
│   ├── events/  listeners/  jobs/  notifications/  commands/
│   ├── providers/           app_service_provider.py (demo, registered in main.py)
│   └── schedule.py           empty Schedule() — used by `pyforge schedule:run`
├── routes/
│   ├── api.py               mounted at /api
│   └── web.py                mounted at /
├── config/
│   └── app.py database.py auth.py cache.py mail.py queue.py storage.py
├── database/
│   ├── migrations/          env.py, script.py.mako, versions/
│   └── seeders/             database_seeder.py
├── tests/
│   └── test_welcome.py        a real, passing test
├── storage/
├── .env  .env.example
├── pyproject.toml
├── Dockerfile  .dockerignore
├── .gitignore
├── README.md
└── main.py                     constructs PyForge(), registers routes/providers
```

`main.py` is directly ASGI-runnable — `uvicorn main:app` and `pyforge serve`
both work without further configuration, and `pytest` passes out of the box.

## Extending the CLI (third-party commands)

The CLI discovers additional commands from the `pyforge.commands`
[entry-point group](https://packaging.python.org/en/latest/specifications/entry-points/):

```toml
# your package's pyproject.toml
[project.entry-points."pyforge.commands"]
auth = "pyforge_auth.commands:register"
```

```python
# pyforge_auth/commands.py
import typer

def register(app: typer.Typer) -> None:
    @app.command(name="auth:make-token")
    def make_token(user_id: int) -> None:
        ...
```

A broken plugin (import error, exception in `register()`) prints a warning
and is skipped — it never prevents the rest of the CLI from working. See
[Extending PyForge](packages.md) for the full package-authoring picture.

!!! note "No `pyforge test` command"
    `pytest` already runs a generated project's test suite with zero extra
    configuration — a wrapper command would only be added if it needed to do
    something `pytest` alone can't (e.g. auto-provisioning a test database).
