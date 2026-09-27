# Development Roadmap

PyForge is built incrementally, in the phases below. Every other document in
`docs/architecture/` links back here to mark what's implemented today versus
designed-but-not-built. Treat this file as the single source of truth for
"is X real yet?" — if a feature is claimed anywhere else in the docs without
a checkmark here, that's a documentation bug.

Semantic Versioning applies from `0.1.0`. Everything before `1.0.0` may still
change shape; APIs that are especially likely to shift are called out in
[03-public-api-design.md](03-public-api-design.md).

## Phase 1 — Foundation ✅ (this release, `0.1.0`)

- [x] `PyForge` application core, wrapping a real `fastapi.FastAPI` instance
- [x] Dependency-injection `Container` (bind, singleton, instance, autowiring)
- [x] Configuration (`config/*.py` namespaces + `.env` loading + `config()`/`env()` helpers)
- [x] `Router` / `RouteGroup` (named routes, prefixes, controller-action wiring)
- [x] Named, route-scoped middleware registry (FastAPI dependencies by name)
- [x] `ServiceProvider` (register/boot lifecycle tied to app startup)
- [x] `pyforge` CLI (Typer-based, third-party-extensible via entry points)
- [x] Project generator: `pyforge new` / `pyforge init`
- [x] `pyforge serve`, `pyforge route:list`
- [x] `pyforge make:controller|middleware|provider|command`
- [x] Full FastAPI interop: `app.fastapi`, `@app.get(...)`, `app` itself is ASGI-callable
- [x] Unit tests for the container, config, router, and application core
- [x] Working generated project (`main.py` boots and serves real requests)

## Phase 2 — Database ✅ (`0.2.0`)

- [x] SQLAlchemy 2.x engine/session integration per `config/database.py`
      (sync, not async — see [06-database-architecture.md](06-database-architecture.md#sync-not-async--a-deliberate-choice))
- [x] `Model` base class (Active-Record-style: `User.find(1)`, `User.create(...)`)
- [x] Query builder (`User.query().where(...).paginate(...)`) over SQLAlchemy Core
- [x] Relationships: `has_one`, `has_many`, `belongs_to`, `belongs_to_many`, explicit eager loading (`.with_(...)`)
- [x] Alembic-backed migrations with a schema-builder DSL (`table.string("name")`, ...)
- [x] `pyforge migrate`, `migrate:make`, `migrate:rollback`, `migrate:status`
- [x] Model factories and seeders, `pyforge db:seed`
- [x] Soft deletes, timestamps, UUID/ULID primary keys (base classes, not mixins, for the PK strategies)
- [x] `pyforge make:model` (with `--migration`), `make:migration`
- [x] Automatic per-request database session (zero explicit wiring in controllers)
- [ ] `Model.query(...)`'s async equivalent — intentionally not planned; see the doc above
- [ ] Autogenerate-based `migrate:make` — intentionally deferred, not planned as default behavior

See [06-database-architecture.md](06-database-architecture.md) for the full picture.

## Phase 3 — API layer ✅ (`0.3.0`)

- [x] `FormRequest` (string-rule validation) alongside native Pydantic models —
      a `FormRequest`-typed controller parameter is auto-injected as a
      dependency by `Router`, no `Depends(...)` needed
- [x] API `Resource` transformers (`.make`, `.collection`, `.paginated`)
- [x] Pagination response envelope (`data` + `meta`) — `Resource.paginated(paginator)`
- [x] Centralized exception → HTTP response mapping — `ModelNotFoundError` → 404,
      `PyForgeError` → 500 (detail only when `config("app.debug")`), registered
      automatically on every `PyForge` app
- [x] `pyforge make:schema`, `make:request`, `make:resource`

## Phase 4 — Authentication & authorization ✅ (`0.4.0`, optional module)

- [x] `pyforge.auth`: JWT access/refresh tokens, password hashing (bcrypt),
      `Auth.attempt`/`.login`/`.refresh` — ships as an opt-in module in the
      same distribution for now (`pip install pyforge-framework[auth]`), not
      a separate PyPI package yet — see
      [05-plugin-package-architecture.md](05-plugin-package-architecture.md)
- [x] API tokens (`ApiTokenAuth`, Sanctum-style personal access tokens)
- [x] Cookie-based session authentication (`Auth.session_login`/`.session_required`)
- [x] Signed, purpose-scoped tokens for email verification / password reset
      (`Auth.make_signed_token`/`.verify_signed_token`) — actually *sending*
      the email is a Phase 5 (Mail) concern
- [x] Policy classes + `authorize(...)`, `@permission(...)` / `@role(...)` guards
- [x] `current_user` — a `Depends(...)`-ready dependency resolving whichever
      `Auth` was registered via `set_default_auth(...)`, independent of
      import order
- [x] `pyforge make:policy`
- [ ] OAuth2 as a full provider (authorization-code flow, client
      registration, scopes) or third-party login (Google/GitHub/...) —
      only `OAuth2PasswordBearer`-compatible Swagger UI integration for the
      JWT bearer flow is implemented; a real OAuth2 server/client is a
      substantially larger, separately-scoped feature

## Phase 5 — Application infrastructure ✅ (`0.5.0`, optional modules)

- [x] Cache: `Cache.get`/`.put`/`.forget`/`.remember`/`.flush`, memory/file/Redis
      drivers, `pyforge cache:clear` — no database-backed driver (memory,
      file, and Redis cover the realistic cases; a fourth driver purely for
      "no Redis available" wasn't worth the extra surface)
- [x] Event bus: `event(...)` (async) + `listen(...)`, sync and async
      listeners both supported — `event(...)` is `await`-able rather than
      the spec's sync-looking call, for the same reason the ORM is sync
      instead of matching a literal async example: honesty about what the
      call actually does, here in the opposite direction (see
      [03-public-api-design.md](03-public-api-design.md#events-pyforgeevents))
- [x] Queue/jobs: `dispatch(...)`, sync + Redis drivers (`BLPOP`-based
      priority queues), retries + backoff, `pyforge queue:work` — job
      *timeout* enforcement isn't implemented (no reliable, portable way to
      hard-kill a stuck synchronous job without real subprocess isolation,
      which is a bigger feature than this phase's scope)
- [x] Scheduler: `Schedule.every_minute/every_hour/every_day(...).at(...)`,
      a full 5-field cron expression parser, `pyforge schedule:run` —
      stateless by design (matches how a real crontab-driven `schedule:run`
      actually works; no persisted "last run" state to manage)
- [x] Mail: `Mailable`, `Mailer.to(...).send(...)`, a real stdlib-`smtplib`
      SMTP driver plus an `ArrayMailDriver` for tests — SES/Mailgun/Postmark/
      SendGrid adapters aren't built; each is a distinct HTTP API, not an
      SMTP-driver variant, so they're separate, not-yet-started work rather
      than a gap in the SMTP driver itself
- [x] Notifications: `Notification.via(...)`, `notify(...)`, a `mail`
      channel (registered by default) and a `DatabaseNotificationChannel` —
      no webhook channel yet
- [x] Storage: `Storage.put`/`.get`/`.delete`/`.url`/`.exists`, a local
      driver (with path-traversal protection) and an S3 driver (also covers
      R2 and other S3-compatible stores via `endpoint_url`) — no dedicated
      Azure Blob/GCS drivers
- [x] `pyforge make:job`, `make:event`, `make:listener`, `make:notification`
- [x] All seven modules ship in the same `pyforge-framework` distribution as
      opt-in submodules (`from pyforge.cache import ...`, etc.), not
      separate PyPI packages yet — same reasoning as Phase 4's `pyforge.auth`

## Phase 6 — Developer ecosystem ✅ (`0.6.0`)

- [x] CLI plugin discovery via the `pyforge.commands` entry-point group
- [x] `pyforge.tenancy` — multi-tenancy, both strategies from the original
      spec: `TenantScopedMixin` (shared database, `tenant_id` column,
      queries/`create()` auto-scoped to `current_tenant_id()`) and
      `TenantDatabaseManager` (database per tenant, routes `session_scope()`
      to a distinct connection per tenant). This is also this project's
      first real second consumer of the "optional package extends core"
      pattern — see [05-plugin-package-architecture.md](05-plugin-package-architecture.md)
- [x] `DatabaseManagerLike` protocol added to core `pyforge.database` — a
      small, structural-typing change that let `TenantDatabaseManager` plug
      into `set_current_database()`/`session_scope()` without core ever
      importing `pyforge.tenancy`, and without `TenantDatabaseManager`
      subclassing `DatabaseManager`. The concrete example of how core is
      meant to evolve to support packages: a narrow, generic seam, added
      because a real package needed it — not a speculative extension point
- [x] `pyforge package:install <name>` — a thin wrapper over `pip install`,
      resolving official extras (`auth`/`cache`/`queue`/`storage`) to
      `pyforge-framework[extra]` and anything else to `pyforge-<name>`
- [ ] Full package contract: routes and config contributed by packages
      automatically (today a package can register commands, a
      `ServiceProvider`, and — as of `pyforge.tenancy` — extend a documented
      core protocol; it still can't auto-merge its own `config/*.py`
      defaults, and migrations remain app-owned, see
      [05-plugin-package-architecture.md](05-plugin-package-architecture.md))
- [ ] `pyforge-admin` — a real, separately-scoped UI product, not attempted here

## Phase 7 — Production readiness ✅ (`0.7.0`, except where noted)

- [x] Broader test-helper library — `pyforge.testing`: `fake_mail()`,
      `fake_queue()`, `fake_events()` (install a recording fake as the
      process default and hand it back for `.assert_pushed`/
      `.assert_dispatched`-style assertions), `assert_status(response, ...)`,
      `assert_json_subset(response, ...)`
- [x] Security hardening pass + documented threat model —
      [10-security.md](10-security.md), walking the original spec's own
      security checklist item-by-item. Two real issues found and fixed
      during the review: `TenantScopedMixin.create()` now force-overwrites
      any caller-supplied `tenant_id` instead of only filling it in when
      absent (closes a mass-assignment path into cross-tenant writes), and
      `Auth.session_login` now defaults to `secure=True` (was sending the
      session cookie over plain HTTP by default). `pyforge.security` is a
      new optional module: `rate_limit("60/minute")` (fixed-window, via the
      configured cache) and `SecurityHeadersMiddleware`. Known, deliberately
      unfixed gaps (no mass-assignment allowlist, the Redis/pickle trust
      boundary) are documented rather than silently left implicit.
- [x] Docker image + deployment recipes — every `pyforge new` project now
      generates a `Dockerfile` + `.dockerignore`; see
      [11-deployment.md](11-deployment.md) for the build, the non-root user,
      the deliberate choice to run migrations as a separate deploy step (not
      at container startup, to avoid concurrent-migration races on a rolling
      deploy), and platform recipes. Verified end-to-end by hand (a real
      image built from the shipped template, run, and `curl`ed for a real
      `200`) — that verification surfaced a real bug: the generated
      `pyproject.toml` had no `[tool.hatch.build.targets.wheel]`
      configuration, so `pip install .` failed for *every* freshly generated
      project (a flat-layout application has no `<name>/` package directory
      for hatchling to auto-detect). Fixed with `bypass-selection = true`;
      see [tests/test_generator.py](../../tests/test_generator.py) for the
      regression test and `docker-smoke-test` in
      [ci.yml](../../.github/workflows/ci.yml) for the now-automated version
      of the same end-to-end check.
- [x] Full CI matrix (lint, type-check, unit + integration tests, build,
      generated-project smoke test, Docker smoke test) — publish is wired
      (`publish.yml`, trusted OIDC publishing) but has never been triggered;
      see the next line
- [ ] Published to PyPI as `pyforge-framework` — deliberately not done as
      part of this phase. Publishing is an irreversible, externally-visible
      action (the name can't be un-published or meaningfully reused if
      squatted or mistaken); `publish.yml` is ready to go the moment a
      maintainer triggers a GitHub release, but that trigger is a decision
      for a human, not something to do automatically because the rest of
      the checklist is done
- [x] End-user documentation site — `docs-site/` (MkDocs + Material),
      published separately from this `docs/architecture/` (see
      [08-documentation-architecture.md](08-documentation-architecture.md)
      for why the two stay split). 21 task-oriented pages covering every
      guide this roadmap lists, a CLI reference, and a Troubleshooting page
      compiled from the real gotchas found while building Phases 1-7
      (the `<locals>` controller-detection trap, the `@role` import-order
      requirement, `secure=True` session cookies over plain HTTP, job
      pickling-by-value, the hatchling `pyproject.toml` bug above). Verified
      end-to-end in a real browser (search, dark mode, mobile layout, code
      copy) before being called done, the same standard applied to the
      Docker verification above. CI runs `mkdocs build --strict` on every
      push (`docs-site-build` in [ci.yml](../../.github/workflows/ci.yml))
      so a broken internal link fails the same way a broken test would.

**Why this project stays at `0.7.0`, not `1.0.0`, now that every phase is
checked off:** reaching the end of a roadmap's phase list is not itself a
reason to declare API stability — that's a promise about the *shape* of the
public API holding steady going forward, which requires real external usage
surfacing the rough edges a single contributor won't find alone, not just a
feature checklist being complete. `1.0.0` should be a deliberate decision
made after PyPI publication and some real-world usage, not an automatic
next step.

## Explicit non-goals

These are permanent, not "later":

- Reimplementing FastAPI, Starlette, SQLAlchemy, Alembic, or cryptography primitives.
- Hiding FastAPI from developers who want it directly.
- A single "one true way" — beginner (`User.create(...)`), intermediate
  (`User.query().where(...)`), advanced (raw SQLAlchemy `session`), and FastAPI-expert
  (`app.fastapi.get(...)`) usage must all keep working, forever.
