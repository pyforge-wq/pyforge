# Extending PyForge

PyForge is designed as an ecosystem, not a monolith: `pip install
pyforge-framework` gets you the core; anything past that is a separate,
independently versioned `pyforge-*` package (or, for now, one of the
optional modules — `auth`, `cache`, `events`, `queue`, `scheduler`, `mail`,
`notifications`, `storage`, `tenancy`, `security`, `testing` — shipped
inside the same distribution but never imported unless you ask for them).

## What a package can hook into today

### 1. CLI commands

Via the `pyforge.commands` entry-point group — see
[CLI Reference](cli-reference.md#extending-the-cli-third-party-commands). A
broken or missing plugin degrades to a warning, never a crash. Namespace
your commands by convention (`yourpkg:command-name`) to avoid collisions.

### 2. Bindings, config, and routes — via a `ServiceProvider`

```python
# in the app's main.py
from pyforge_stripe import StripeServiceProvider
app.register(StripeServiceProvider)
```

```python
# inside pyforge_stripe
class StripeServiceProvider(ServiceProvider):
    def register(self) -> None:
        self.app.container.singleton(PaymentGateway, StripeGateway)

    def boot(self) -> None:
        router = Router(container=self.app.container)
        router.post("/webhooks/stripe", StripeWebhookController.handle)
        self.app.register_routes(router, prefix="/api")
```

`ServiceProvider.boot()` receives the real `PyForge` app (`self.app`) with a
live container and `register_routes` — this is the whole integration
surface, and it's enough for a package to bind services, add routes, and
register middleware.

### 3. A narrow, structural seam in core — only when a real package needs one

`pyforge.tenancy`'s `TenantDatabaseManager` (database-per-tenant) needed to
plug into `session_scope()` the same way the default `DatabaseManager` does,
without subclassing it. Core's answer was `DatabaseManagerLike` — a
`typing.Protocol` listing exactly the methods `session_scope()` calls.
`set_current_database()` accepts anything satisfying that shape, and core
still never imports `pyforge.tenancy`. This is the pattern for any future
case like it: a real package hits a real limit, core grows the smallest
structural seam that fixes it — added because something needed it, not in
anticipation that something might.

## What a package can't do yet

- **Ship its own Alembic migrations that `pyforge migrate` picks up
  automatically.** `pyforge migrate` only ever looks at the app's own
  `database/migrations/versions/`. A package needing tables documents a
  migration for the app to copy in, or provides a helper the app imports.
- **Contribute default `config/*.py` values that merge with the app's own
  config.** Config is only ever loaded from the app's `config/` directory —
  a package wanting configuration documents its own `env()` keys and asks
  the app to add them, or reads `os.environ` directly in its own provider.
- **Be auto-discovered without the app explicitly calling
  `app.register(SomeServiceProvider)`.** There's deliberately no
  "install and it just activates" magic yet. "Install and wire up two or
  three lines in `main.py`" remains the documented, supported way to
  consume a package.

## Naming convention

- Core: `pyforge` (PyPI: `pyforge-framework`, import: `pyforge`).
- Official packages: `pyforge-auth`, `pyforge-tenancy`, `pyforge-queue`,
  `pyforge-mail`, `pyforge-storage`, `pyforge-notifications`,
  `pyforge-broadcast`, `pyforge-admin`, `pyforge-testing`.
- Third-party packages: any `pyforge-<name>` on PyPI, importable as
  `pyforge_<name>` (Python identifiers can't contain hyphens). Nothing
  enforces this prefix — it's a discoverability convention.

Install an official extra with the CLI's own wrapper:

```bash
pyforge package:install auth      # -> pip install "pyforge-framework[auth]"
pyforge package:install some-pkg  # -> pip install pyforge-some-pkg
```

## Package authoring checklist

A well-behaved PyForge package:

1. Depends on `pyforge-framework` with a version range, never pins it exactly.
2. Exposes one or more `ServiceProvider` subclasses as its integration point.
3. If it adds CLI commands, registers them via `pyforge.commands` entry
   points, namespaced, and never mutates global Typer/Click state outside
   its own `register(app)` function.
4. Never imports application code (`app.controllers`, etc.) — packages
   depend on the framework, never on a specific generated project.
5. Ships its own tests against a minimal `PyForge()` instance (see
   [Testing](testing.md)), not against a real generated project.

## Why this shape

The core rule: *if a majority of real apps would never enable it, it's a
package.* That only works if packages have a real, load-bearing way to
integrate. `ServiceProvider` plus CLI entry points is deliberately the
*smallest* mechanism that satisfies that — a container to bind into, routes
to add, commands to expose. Richer package manifests (auto-merged config,
auto-discovered migrations) get added only when a real package needs them,
not speculatively.
