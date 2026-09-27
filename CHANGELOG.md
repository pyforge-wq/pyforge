# Changelog

All notable changes to this project are documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/).

## [0.7.0] - Phase 7: Production readiness

### Added

- `pyforge.testing`: `fake_mail()`, `fake_queue()`, `fake_events()` (install
  a recording fake as the process default), `FakeQueueDriver`/
  `FakeEventDispatcher` (`.assert_pushed`/`.assert_dispatched` and their
  `_not_` counterparts), `assert_status(response, ...)`,
  `assert_json_subset(response, ...)`.
- `pyforge.security`: `rate_limit("60/minute", key_func=..., cache=...)` —
  a fixed-window counter over the configured `Cache` — and
  `SecurityHeadersMiddleware` (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security` on
  HTTPS; never overrides a header already set).
- `pyforge.routing.inject_dependency`: the FastAPI-signature-injection
  utility used internally by `@role`/`@permission` was promoted from a
  private `pyforge.auth` helper into a public core utility, so
  `pyforge.security.rate_limit` doesn't need to depend on `pyforge.auth` to
  do the same trick.
- A `Dockerfile` + `.dockerignore` in every `pyforge new` project — see
  [docs/architecture/11-deployment.md](docs/architecture/11-deployment.md)
  for the build, the non-root user, and why migrations run as a separate
  deploy step rather than at container startup.
- `docs/architecture/10-security.md`: a manual security review against the
  original spec's own checklist, item-by-item, including what's
  deliberately not built and why.
- `docs/architecture/11-deployment.md`: the Docker image, environment
  configuration, and platform recipes.
- CI: a `docker-smoke-test` job that generates a real project, builds a
  real framework wheel, builds the generated `Dockerfile`, runs it, and
  `curl`s it for a real response.
- `docs-site/`: the end-user documentation site (MkDocs + Material) — 21
  task-oriented pages covering every guide, a full CLI reference, and a
  Troubleshooting page built from the real gotchas found across Phases 1-7
  (the `<locals>` controller-detection trap, the `@role` import-order
  requirement, `secure=True` session cookies over plain HTTP, job
  pickling-by-value, and more). Verified in a real browser (search, dark
  mode, mobile layout) before being called done. CI runs
  `mkdocs build --strict` (`docs-site-build` job) so a broken internal link
  fails the same way a broken test would. Not yet deployed to a public URL —
  that's a separate, human-triggered decision, same as PyPI publishing.

### Fixed

- **Tenant isolation / mass assignment**: `TenantScopedMixin.create()` now
  force-overwrites any caller-supplied `tenant_id` instead of only filling
  it in when absent — closes a path where a spoofed `tenant_id` in request
  data (e.g. `Post.create(**request.validated())`) could write into another
  tenant's rows. Found during the Phase 7 security review; see
  `tests/test_tenancy.py`'s `test_create_overrides_a_caller_supplied_tenant_id`.
- **Insecure-by-default session cookie**: `Auth.session_login` now defaults
  to `secure=True` (was sending the session cookie over plain HTTP). Pass
  `secure=False` explicitly for local `http://localhost` development.
- **Generated projects couldn't be `pip install`ed**: the generated
  `pyproject.toml` had no `[tool.hatch.build.targets.wheel]` configuration,
  so `pip install .` failed for every freshly generated project — a
  flat-layout application (`main.py`, `routes/`, `config/` at the top
  level) has no `<project_name>/` package directory for hatchling to
  auto-detect, and nothing in the existing test suite or CI ever actually
  built a generated project's own wheel to catch it. Found while hand-
  verifying the new Dockerfile end-to-end. Fixed with
  `bypass-selection = true`; regression-tested in
  `tests/test_generator.py` and covered going forward by the new
  `docker-smoke-test` CI job.
- `pyforge new` now generates a real random `JWT_SECRET`
  (`secrets.token_urlsafe(32)`) into `.env` instead of a static
  `change-me` placeholder; `.env.example` (meant to be committed) keeps the
  placeholder.

### Notes

- Still pre-`1.0.0` on purpose: every roadmap phase is now checked off, but
  reaching the end of a checklist isn't itself a reason to promise API
  stability — see
  [09-roadmap.md](docs/architecture/09-roadmap.md#phase-7--production-readiness--070-except-where-noted).
- PyPI publishing (`publish.yml`) is wired and ready but has not been
  triggered — that's a deliberate, separate decision, not part of this
  release.

## [0.6.0] - Phase 6: Developer ecosystem

### Added

- `pyforge.tenancy`: multi-tenancy, both strategies from the original spec —
  `TenantScopedMixin` (shared database, `tenant_id` column; `Model.query()`/
  `.create()` auto-scoped to `current_tenant_id()`, so every read/write
  through it is confined to the current tenant with no per-call escape
  hatch) and `TenantDatabaseManager` (database per tenant, routes
  `session_scope()` to a distinct connection per tenant). Plus
  `TenantResolutionMiddleware`, `subdomain_tenant_resolver`,
  `header_tenant_resolver`, and `tenant_scope(...)`.
- `DatabaseManagerLike`: a `typing.Protocol` added to core `pyforge.database`,
  capturing exactly what `session_scope()` needs (`engine`/`session_factory`/
  `dispose`). Lets `TenantDatabaseManager` plug into `set_current_database()`
  without subclassing `DatabaseManager` and without core ever importing
  `pyforge.tenancy` — the concrete pattern for how core is meant to grow to
  support packages going forward (see docs/architecture/05-plugin-package-architecture.md).
- `pyforge package:install <name>`: a thin `pip install` wrapper resolving
  official extras (`auth`/`cache`/`queue`/`storage`) to
  `pyforge-framework[extra]` and anything else to `pyforge-<name>`.
- Test suite: `test_tenancy.py` (11 tests, covering both strategies and the
  resolution middleware) and `test_package_install_command.py`.

## [0.5.0] - Phase 5: Application infrastructure

Seven independent, optional modules — none imported by `import pyforge`,
none imported by each other except `pyforge.notifications`' mail channel.
See [docs/architecture/03-public-api-design.md](docs/architecture/03-public-api-design.md)'s
new section and [09-roadmap.md](docs/architecture/09-roadmap.md).

### Added

- `pyforge.cache`: `Cache`, memory/file/Redis drivers (`redis` extra),
  `pyforge cache:clear`, `config:clear`.
- `pyforge.events`: `EventDispatcher`, `Listener`, `event()` (async — see
  the architecture doc for why), `listen()`. Both sync and async listeners.
- `pyforge.queue`: `Job`, `Worker` (retries + backoff), sync + Redis drivers
  (`BLPOP`-based priority queues, `queue` extra), `dispatch()`,
  `pyforge queue:work`, `make:job`.
- `pyforge.scheduler`: `Schedule` (`every_minute`/`every_hour`/`every_day().at(...)`),
  a from-scratch 5-field cron expression parser, `pyforge schedule:run`
  (stateless — matches how a real crontab-driven scheduler works).
- `pyforge.mail`: `Mailable`, `Mailer`/`PendingMail`, a real stdlib-`smtplib`
  SMTP driver, an `ArrayMailDriver` for tests.
- `pyforge.notifications`: `Notification`, `notify()`, `MailChannel`
  (registered by default), `DatabaseNotificationChannel`.
- `pyforge.storage`: `Storage`, a path-traversal-checked local driver, an S3
  driver (also covers R2/other S3-compatible stores, `storage` extra).
- `pyforge make:event`, `make:listener`, `make:notification`.
- Generated projects now ship `app/schedule.py` and `config/storage.py`;
  `config/cache.py`/`mail.py`/`queue.py`/`auth.py` lost their stale "not
  implemented yet" comments now that the corresponding modules are real.
- New optional dependency groups: `cache`, `queue` (both `redis`), `storage`
  (`boto3`). New dev-only test dependencies: `fakeredis`, `moto[s3]`,
  `aiosmtpd` — used to verify the Redis, S3, and SMTP drivers for real
  (against an in-memory Redis, a mocked S3 bucket, and a genuine local SMTP
  server) rather than only unit-testing the code that builds the requests.
- Test suite: `test_cache.py`, `test_events.py`, `test_queue.py`,
  `test_scheduler.py`, `test_mail.py`, `test_notifications.py`,
  `test_storage.py` (85 new tests).

## [0.4.0] - Phase 4: Authentication & authorization

An *optional* module, `pyforge.auth` — not imported by `import pyforge`,
requires `pip install pyforge-framework[auth]` (bcrypt, PyJWT). See
[docs/architecture/03-public-api-design.md](docs/architecture/03-public-api-design.md)'s
auth section and [09-roadmap.md](docs/architecture/09-roadmap.md).

### Added

- `Auth`: password hashing (bcrypt) + JWT access/refresh tokens —
  `.attempt(email, password)`, `.login(user)`, `.refresh(token)`,
  `.required`/`.optional` (bearer-token dependencies, wired to
  `OAuth2PasswordBearer` for Swagger UI's "Authorize" button).
- Cookie-based session authentication: `Auth.session_login`/`.session_required`.
- Signed, purpose-scoped tokens for email verification / password reset:
  `Auth.make_signed_token`/`.verify_signed_token` (sending the email is a
  Phase 5 concern).
- `ApiTokenAuth`: Sanctum-style personal access tokens, wired to whatever
  token/user models the app defines.
- `Policy` + `authorize(...)`, and `@role(...)`/`@permission(...)`
  decorators — implemented via the same signature-injection technique
  `Router` already uses for controller actions and `FormRequest`.
- `current_user`: a `Depends(...)`-ready dependency resolving the default
  `Auth` (via `set_default_auth(...)`) at request time, so it works
  regardless of module import order — unlike the decorator form, which
  resolves at class-definition time (documented import-order rule).
- `pyforge make:policy`.
- The generated project's `main.py` now registers providers *before*
  importing `routes/`, so a provider that configures `Auth` from `config(...)`
  (or any decorator that depends on it) works correctly by default.
- Test suite: `tests/test_auth.py` (13 tests) — login, refresh, bearer and
  session-cookie guards, role/permission decorators (explicit and default
  auth), policies, and API tokens, all verified against a real `TestClient`.

## [0.3.0] - Phase 3: API layer

### Added

- `FormRequest` (`pyforge.validation`): pipe-separated rule
  validation (`required`, `string`, `integer`, `numeric`, `boolean`, `email`,
  `url`, `min:N`, `max:N`, `in:a,b,c`, `confirmed`, `unique:table[,column]`).
  A controller (or plain function route) parameter typed as a `FormRequest`
  subclass is auto-injected as a FastAPI dependency by `Router` — no
  `Depends(...)` needed; a validation failure raises `HTTPException(422)`.
- `Resource` (`pyforge.resources`): API transformers — `.make(model)`,
  `.collection(models)`, `.paginated(paginator)` (bridges `QueryBuilder`'s
  `Paginator` straight to the `{"data": [...], "meta": {...}}` envelope).
- Centralized exception handling, registered automatically on every
  `PyForge` app: `ModelNotFoundError` → 404, `PyForgeError` → 500 (detail
  only when `config("app.debug")`).
- `pyforge make:schema`, `make:request`, `make:resource`.
- Test suite: `test_validation.py`, `test_form_request_routing.py`,
  `test_resource.py`, `test_exception_handlers.py` — the routing tests
  verify FormRequest injection against a real `TestClient`, for both
  controller actions and plain function routes.

## [0.2.0] - Phase 2: Database

Adds the ORM, query builder, migrations, and factories/seeders on top of
Phase 1. See [docs/architecture/06-database-architecture.md](docs/architecture/06-database-architecture.md)
and the updated [docs/architecture/09-roadmap.md](docs/architecture/09-roadmap.md).

### Added

- `DatabaseManager`: builds/caches a synchronous SQLAlchemy `Engine` +
  `sessionmaker` per named connection from `config/database.py` (sqlite,
  mysql, postgresql URL builders).
- Automatic per-request database session (`DatabaseSessionMiddleware`,
  `session_scope()`, `current_session()`) — wired into `PyForge.__init__`
  with zero developer configuration whenever `config/database.py` exists.
- `Model` (+ `UUIDModel`, `ULIDModel`): an Active-Record-style base over
  SQLAlchemy 2.0 declarative classes (`all`, `find`, `find_or_fail`,
  `where`, `create`; instance `save`/`update`/`delete`).
- `QueryBuilder` and `Paginator`: a fluent, chainable query builder
  (`where`, `or_where`, `where_in`, `where_null`, `where_between`,
  `order_by`, `group_by`, `having`, `join`, `left_join`, `select`, `limit`,
  `offset`, `with_`) with `get`/`first`/`find`/`count`/`exists`/`paginate`.
- `has_one`, `has_many`, `belongs_to`, `belongs_to_many`: named wrappers
  over SQLAlchemy `relationship()`.
- `TimestampsMixin`, `SoftDeletesMixin`.
- `Schema`/`TableBuilder`/`Column`: a migration-time schema-builder DSL over
  real Alembic `op.*` operations, with a custom Mako script template that
  pre-fills a working migration skeleton from the migration's name.
- `pyforge migrate`, `migrate:make`, `migrate:rollback`, `migrate:status`.
- `pyforge make:model` (with `--migration`), `make:migration` (alias).
- `pyforge db:seed`.
- `Factory` and `Seeder` base classes — `UserFactory.create()`,
  `.create_batch(n)`, and instance-level trait chaining
  (`UserFactory().admin().create()`) all work from one method body via a
  small custom descriptor.
- An in-house `generate_ulid()` (Crockford-base32 ULID) — no new dependency
  for something this small and stable.
- New core dependencies: `sqlalchemy`, `alembic`, `pymysql`.
- Generated projects now ship a real `database/migrations/env.py` +
  `script.py.mako` and `database/seeders/database_seeder.py`.
- Test suite: `test_database_manager.py`, `test_orm.py`, `test_schema.py`,
  `test_factory_seeder.py`, `test_database_integration.py` — the last one
  proves the automatic per-request session against a real HTTP request,
  including rollback-on-exception.

### Fixed

- The migration DSL's `.default(value)`/`.timestamps()` initially used
  SQLAlchemy's client-side-only `default=`, which is a no-op for anything
  inserted outside the exact (migration-local, discarded) `Column` object —
  found via end-to-end testing as a `NOT NULL constraint failed` on a bare
  insert. Fixed to use a real `server_default`, and `.timestamps()` columns
  are now nullable (populating them is `TimestampsMixin`'s job, not the
  schema's) — see the regression test in `tests/test_schema.py`.

## [0.1.0] - Phase 1: Foundation

Initial release. See [docs/architecture/09-roadmap.md](docs/architecture/09-roadmap.md)
for the full phase breakdown.

### Added

- `PyForge` application core wrapping a real `fastapi.FastAPI` instance,
  ASGI-callable directly, with `.fastapi`/`.fastapi_app` always reachable.
- `Container`: dependency injection with `bind`/`singleton`/`instance`/`make`
  and constructor autowiring.
- Configuration: `Config` repository loaded from `config/*.py` namespaces,
  `.env` loading via `load_env()`, `env()`/`config()` helpers.
- `Router` / `RouteGroup`: HTTP-verb registration, named routes, route
  groups with prefix/middleware/name scoping, automatic controller-action
  wiring (an unbound method like `UserController.show` is resolved fresh
  from the container per request).
- `MiddlewareRegistry`: named, route-scoped FastAPI-dependency middleware.
- `ServiceProvider`: two-phase `register()`/`boot()` lifecycle tied to
  application startup.
- `pyforge` CLI (Typer-based): `new`, `init`, `serve`, `route:list`,
  `make:controller`, `make:middleware`, `make:provider`, `make:command`.
- Third-party CLI extensibility via the `pyforge.commands` entry-point group.
- Project generator producing a fully working, immediately runnable and
  testable application.
- Architecture documentation (`docs/architecture/`) covering the framework
  architecture, core package layout, public API, CLI, plugin architecture,
  planned database architecture, testing architecture, documentation
  architecture, and roadmap.
- Unit test suite for the container, config, router, and application core.
