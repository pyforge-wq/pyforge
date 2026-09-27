# Plugin / Package Architecture

PyForge is designed as an ecosystem, not a monolith: `pip install
pyforge-framework` gets you the core in
[02-core-package-architecture.md](02-core-package-architecture.md); anything
past that is a separate, independently versioned `pyforge-*` package.

## What a package can hook into today

1. **CLI commands**, via the `pyforge.commands` entry-point group — see
   [04-cli-specification.md](04-cli-specification.md#extensibility-third-party-commands).
   This is fully implemented: a broken or missing plugin degrades to a
   warning, never a crash, and commands are namespaced by convention
   (`auth:*`, `tenancy:*`) to avoid collisions.
2. **Bindings, config, and routes**, via a `ServiceProvider` the *application*
   explicitly registers:

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

   This works today because `ServiceProvider.boot()` receives the real
   `PyForge` app (`self.app`) with a live container and `register_routes`.

3. **A narrow, structural seam in core, when a real package needs one.**
   `pyforge.tenancy`'s `TenantDatabaseManager` (database-per-tenant) needed
   to plug into `session_scope()` the same way the default `DatabaseManager`
   does, without subclassing it. Core's answer was `DatabaseManagerLike` — a
   `typing.Protocol` in `pyforge/database/manager.py` listing exactly the
   three methods `session_scope()` actually calls. `set_current_database()`
   now accepts anything satisfying that shape. Core still never imports
   `pyforge.tenancy` — the dependency arrow didn't flip, it just got a
   documented crack for a real package to fit through. This is the pattern
   for every future case like it: a real package hits a real limit, core
   grows the smallest seam that fixes it, added because something needed it
   rather than in anticipation that something might.

## What's designed but not automatic yet

A package **cannot yet**:

- Ship its own Alembic migrations that `pyforge migrate` picks up
  automatically — `pyforge migrate` (implemented, Phase 2) only ever looks at
  the app's own `database/migrations/versions/`; a package needing tables
  has to document a migration for the app to copy in, or ask the app to
  import a helper it provides.
- Contribute default `config/*.py` values that merge with the app's own
  config (today, config is only ever loaded from the app's `config/`
  directory; a package wanting configuration must document its own
  `env()` keys and ask the app to add them, or read `os.environ` directly in
  its own provider).
- Be auto-discovered without the application explicitly calling
  `app.register(SomeServiceProvider)` — there is intentionally no
  "install and it just activates" magic yet, the kind of automatic package
  discovery some other frameworks offer. `pyforge.auth`, `pyforge.tenancy`, and the rest of the
  Phase 5 modules are now real packages (albeit shipped inside the same
  distribution) that could validate an entry-point-based discovery
  mechanism (e.g. `pyforge.providers`) — it's deferred a while longer still,
  because none of them have actually needed it: every one of them is
  configured with app-specific values (a secret, a bucket name, a tenant
  resolver) that a `register()` call in `main.py` has to supply anyway, so
  auto-registration wouldn't remove real boilerplate yet. Worth revisiting
  once a package exists that's genuinely zero-config.

"Install and wire up two or three lines in `main.py`" remains the
documented, supported way to consume a package — see
[09-roadmap.md](09-roadmap.md) (Phase 6) for what that phase did and didn't
change about it.

## Naming convention

- Core: `pyforge` (PyPI: `pyforge-framework`, import: `pyforge`).
- Official packages: `pyforge-auth`, `pyforge-tenancy`, `pyforge-queue`,
  `pyforge-mail`, `pyforge-storage`, `pyforge-notifications`,
  `pyforge-broadcast`, `pyforge-admin`, `pyforge-testing`.
- Third-party packages: any `pyforge-<name>` on PyPI, importable as
  `pyforge_<name>` (Python identifiers can't contain hyphens). Nothing
  requires this prefix — it's a discoverability convention, not an
  enforced namespace.

## Package authoring checklist

A well-behaved PyForge package:

1. Depends on `pyforge-framework` with a version range, never pins it exactly.
2. Exposes one or more `ServiceProvider` subclasses as its integration point.
3. If it adds CLI commands, registers them via `pyforge.commands` entry
   points, namespaced (`yourpkg:command-name`), and never mutates global
   Typer/Click state outside its own `register(app)` function.
4. Never imports application code (`app.controllers`, etc.) — packages
   depend on the framework, never on a specific generated project.
5. Ships its own tests against a minimal `PyForge()` instance (see
   [07-testing-architecture.md](07-testing-architecture.md)), not against a
   real generated project.

## Why this shape

The core rule from
[02-core-package-architecture.md](02-core-package-architecture.md) — "if a
majority of real apps would never enable it, it's a package" — only works if
packages have a real, load-bearing way to integrate. `ServiceProvider` plus
CLI entry points is deliberately the *smallest* mechanism that satisfies
that: a container to bind into, routes to add, and commands to expose. Every
official package planned in
[09-roadmap.md](09-roadmap.md) is buildable on exactly this mechanism today;
richer package manifests (auto-merged config, auto-discovered migrations)
are added only when a real package needs them, not speculatively.
