# CLI Specification

The `pyforge` CLI is built on [Typer](https://typer.tiangolo.com/). Run
`pyforge --help` or `pyforge <command> --help` for live usage; this document
is the reference for what exists and what's planned.

## Implemented (Phase 1 through Phase 6)

### `pyforge new NAME [--path PATH]`

Creates a new project directory `NAME` (under `PATH`, defaulting to the
current directory) and scaffolds a full project from the built-in template
(see [Project layout](#generated-project-layout) below). Fails loudly if the
target directory already exists and is non-empty.

### `pyforge init [NAME]`

Same scaffolding as `new`, but into the **current** directory instead of a
new one. `NAME` defaults to the current directory's name and is only used
for `{{ project_name }}` substitutions (e.g. `config/app.py`'s default
`APP_NAME`). Fails if the current directory is non-empty.

### `pyforge serve [--host HOST] [--port PORT] [--reload/--no-reload] [--app MODULE:ATTR]`

Runs the project's app with uvicorn. Defaults: `127.0.0.1:8000`, reload on,
`main:app`. Equivalent to `uvicorn main:app --reload` but discovers the
project root via `--app-dir` so it works regardless of what installed
`pyforge` (a venv it isn't part of, `pipx`, etc.).

### `pyforge route:list [--app MODULE:ATTR]`

Prints every route in the project's OpenAPI schema (method + path) as a
table. Reads the schema rather than walking FastAPI's internal route tree,
so it stays correct across FastAPI versions regardless of how deeply routers
are nested via `include_router`.

### `pyforge make:controller NAME`

Generates `app/controllers/<snake_case>.py` with a `<PascalCase>Controller`
class (suffix `Controller` added automatically if missing — `User` and
`UserController` both produce `UserController`).

### `pyforge make:middleware NAME`

Generates `app/middleware/<snake_case>.py`: an async FastAPI-dependency
function meant to be registered with `app.middleware.register(name, fn)`
and used via `router.group(middleware=[name])`.

### `pyforge make:provider NAME`

Generates `app/providers/<snake_case>.py` with a `<PascalCase>ServiceProvider`
subclass of `ServiceProvider` (suffix `ServiceProvider` added automatically
if missing).

### `pyforge make:command NAME`

Generates `app/commands/<snake_case>.py` with a `<PascalCase>` class with an
async `handle()` method. **Not yet auto-discovered or runnable from the
CLI** — see the caveat in the generated file and [09-roadmap.md](09-roadmap.md).

### `pyforge make:model NAME [--migration/-m]`

Generates `app/models/<snake_case>.py` with a `<PascalCase>` subclass of
`Model`. Table name is naively pluralized (`User` → `users`; rename
`__tablename__` yourself for irregular plurals — see
[06-database-architecture.md](06-database-architecture.md)). With
`--migration`, also creates a matching `create_<table>_table` migration
(equivalent to running `migrate:make create_<table>_table` right after).

### `pyforge migrate:make NAME` (alias: `pyforge make:migration NAME`)

Creates a new, timestamped migration file in
`database/migrations/versions/`, using Alembic's real revision machinery
(`alembic.command.revision`) against a `Config` built programmatically — no
`alembic.ini` needed. If `NAME` matches `create_<table>_table`, the
generated file is pre-filled with a working `Schema.create("<table>")`
skeleton (`table.id()` + `.timestamps()`); any other name gets a generic
`Schema.table(...)` ALTER-style skeleton. See
[06-database-architecture.md](06-database-architecture.md#5-migrations-pyforgedatabaseschemaschema-pyforgedatabasemigrations).

### `pyforge migrate`

Runs every pending migration (`alembic.command.upgrade(cfg, "head")`)
against the connection `database/migrations/env.py` resolves from
`config/database.py` — the same connection the running app uses.

### `pyforge migrate:rollback [--step N]`

Rolls back the last `N` migrations (default 1).

### `pyforge migrate:status`

Prints the current revision and full migration history.

### `pyforge db:seed [--class DOTTED.PATH]`

Runs a seeder's `run()` inside a `session_scope()` (the same auto-committing
session every HTTP request gets). Defaults to
`database.seeders.database_seeder.DatabaseSeeder`, which every generated
project ships (empty, ready to fill in).

### `pyforge make:schema NAME`

Generates `app/schemas/<snake_case>.py` with a `<PascalCase>Schema` — a
native Pydantic `BaseModel` (suffix `Schema` added automatically if missing).

### `pyforge make:request NAME`

Generates `app/requests/<snake_case>.py` with a `<PascalCase>Request`
subclass of `FormRequest` (suffix `Request` added automatically if missing).

### `pyforge make:resource NAME`

Generates `app/resources/<snake_case>.py` with a `<PascalCase>Resource`
subclass of `Resource` (suffix `Resource` added automatically if missing).

### `pyforge make:policy NAME`

Generates `app/policies/<snake_case>.py` with a `<PascalCase>Policy`
subclass of `Policy` (suffix `Policy` added automatically if missing).
Requires the optional auth extra: `pip install pyforge-framework[auth]`.

### `pyforge cache:clear`

Flushes the configured cache driver (`pyforge.cache.make_cache(config("cache")).flush()`).
Requires the optional cache extra only for the Redis driver.

### `pyforge config:clear`

Clears `config/__pycache__`'s compiled bytecode — PyForge doesn't cache
parsed config across processes (`Config.load_directory()` always re-reads
from disk), so this is mainly useful after editing a config file and seeing
stale behavior from a stray `.pyc`.

### `pyforge queue:work [--queue NAMES] [--max-jobs N] [--timeout SECONDS]`

Runs a worker loop against the configured queue driver, retrying failed
jobs per their `max_retries`/`retry_backoff_seconds`. Refuses to run against
the sync driver (nothing would ever be queued to work through). Requires
the optional queue extra for the Redis driver.

### `pyforge schedule:run`

Runs every currently-due task from `app/schedule.py`'s `schedule` object
once, then exits — meant to be invoked by a real OS cron entry every
minute, not to loop itself. Wraps execution in a database session
automatically if `config/database.py` exists.

### `pyforge make:job NAME`, `make:event NAME`, `make:listener NAME`, `make:notification NAME`

Generate, respectively: a `pyforge.queue.Job` in `app/jobs/`, a plain event
class in `app/events/`, a `pyforge.events.Listener` in `app/listeners/`, and
a `pyforge.notifications.Notification` in `app/notifications/`.

### `pyforge package:install NAME`

A thin wrapper over `pip install`: an official extra name (`auth`, `cache`,
`queue`, or `storage`) installs `pyforge-framework[NAME]`; anything else
installs `pyforge-NAME` (or `NAME` as-is if already `pyforge-`-prefixed).
`pyforge.tenancy` has no dedicated CLI commands of its own — everything it
adds is used directly from Python (`TenantScopedMixin`, `TenantResolutionMiddleware`, ...).

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
│   ├── migrations/          env.py, script.py.mako (custom, Schema-DSL-aware), versions/
│   └── seeders/             database_seeder.py (empty, ready to fill in)
├── tests/
│   └── test_welcome.py        a real, passing test against the generated app
├── storage/
├── .env  .env.example
├── pyproject.toml
├── .gitignore
├── README.md
└── main.py                     constructs PyForge(), registers routes/providers
```

`main.py` is directly ASGI-runnable — `uvicorn main:app` and `pyforge serve`
both work without further configuration, and `pytest` passes out of the box.

## Extensibility (third-party commands)

The CLI discovers additional commands from the `pyforge.commands`
[entry-point group](https://packaging.python.org/en/latest/specifications/entry-points/):

```toml
# a third-party package's pyproject.toml
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
and is skipped — it never prevents the rest of the CLI from working. This is
the mechanism [pyforge-auth, pyforge-tenancy, etc.](05-plugin-package-architecture.md)
will use to add their own subcommands (`pyforge tenancy:make`, `pyforge
auth:...`) without any changes to this repository.

## Planned (by phase — see [09-roadmap.md](09-roadmap.md) for detail)

```
test                                                            (Phase 7 — today, `pytest` directly already works)
```

`pyforge test` isn't implemented as a distinct command because `pytest`
already works against a generated project with zero configuration; a
wrapper will only be added if it earns its keep (e.g. auto-loading test
fixtures a later phase introduces), not just to mirror Artisan.
