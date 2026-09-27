# Core Package Architecture

## The test applied to every feature

> Before implementing each major feature, first ask: "does this belong in
> the framework core, or should it be an optional package?"

Applied to the full feature list from the original specification:

| Feature | Core or package? | Why |
|---|---|---|
| Application shell, DI container, config, routing, middleware registry, service providers, CLI | **Core** | Every PyForge app needs these; there is no meaningful app without them. |
| ORM, query builder, migrations | **Core** (implemented, Phase 2) | Not universally required (some apps are pure proxies/gateways), but common enough, and central enough to "convention over configuration," that splitting it into a separate install would hurt the zero-to-running-app experience `pyforge new` promises. Kept as a distinct top-level package (`orm/`, `database/`) inside core so it can still be ignored. |
| Validation | **Core** | Pydantic is already a FastAPI dependency; a `FormRequest` layer on top is a thin core addition, not a new subsystem. |
| Auth, authorization/policies | **Package** (`pyforge.auth`, implemented Phase 4 — ships inside the same distribution today as an *opt-in* module, not auto-imported by `import pyforge`; splitting it into a separate `pyforge-auth` PyPI package is mechanical and will happen before `1.0`) | Auth strategy (JWT vs. session vs. OAuth2) is a real architectural decision per-app; forcing one into core would violate "don't couple optional features to the core." |
| Cache, events, queue/jobs, scheduler, mail, notifications, storage | **Packages** (`pyforge.cache`/`events`/`queue`/`scheduler`/`mail`/`notifications`/`storage`, implemented Phase 5 — same opt-in-module-in-the-same-distribution shape as `pyforge.auth`) | Each has multiple valid backends (Redis vs. memory, SMTP vs. SES, local vs. S3) and zero apps need all of them; bundling would bloat core installs for the common case. |
| Multi-tenancy | **Package** (`pyforge.tenancy`, implemented Phase 6 — same opt-in-module shape) | A significant architectural commitment (query isolation, schema strategy) that most apps don't need. |
| Admin UI | **Package** (`pyforge-admin`) | Purely additive, opinionated UI on top of core primitives. |

Rule of thumb used above: if a feature has more than one legitimate backend
strategy, or if a majority of real apps would never enable it, it's a
package. If literally every generated project needs it to boot, it's core.

## Package layout (implemented today)

```
src/pyforge/
├── __init__.py       Public API surface (see 03-public-api-design.md)
├── core/
│   ├── application.py    PyForge — the application shell
│   └── exceptions.py
├── container/
│   ├── container.py      Container — bind/singleton/instance/make, autowiring
│   └── exceptions.py
├── config/
│   ├── repository.py     Config — dot-notation store, loaded from config/*.py
│   ├── env.py             env() / load_env() — .env parsing with type casting
│   └── helpers.py         config() — global config accessor
├── providers/
│   └── service_provider.py   ServiceProvider — register()/boot() base class
├── routing/
│   ├── router.py          Router — HTTP verbs, controller-action wiring, named routes
│   └── group.py           RouteGroup — prefix/middleware/name scoping (context manager)
├── middleware/
│   └── base.py            MiddlewareRegistry — name → FastAPI dependency
├── database/
│   ├── manager.py         DatabaseManager — Engine/sessionmaker per named connection
│   ├── session.py          session_scope(), current_session(), get_session()
│   ├── middleware.py        DatabaseSessionMiddleware — auto session-per-request
│   ├── schema.py            Schema/TableBuilder/Column — the migration-time DSL
│   └── migrations/          build_alembic_config(), run_migrations() (used by env.py)
├── orm/
│   ├── base.py             Base — the shared SQLAlchemy DeclarativeBase
│   ├── model.py             Model, UUIDModel, ULIDModel — Active-Record base classes
│   ├── query_builder.py      QueryBuilder, Paginator
│   ├── relationships.py       has_one/has_many/belongs_to/belongs_to_many
│   ├── mixins.py             TimestampsMixin, SoftDeletesMixin
│   ├── factory.py            Factory (+ the _HybridMethod descriptor)
│   ├── seeder.py             Seeder
│   └── ulid.py               generate_ulid() — in-house ULID implementation
├── validation/
│   ├── rules.py              validate() — the pipe-separated rule engine
│   └── form_request.py        FormRequest — auto-injected by Router as a dependency
├── resources/
│   └── resource.py           Resource — make/collection/paginated transformers
├── auth/                     optional — not imported by `import pyforge`
│   ├── hashing.py             hash_password/verify_password (bcrypt)
│   ├── jwt.py                  encode_token/decode_token (PyJWT)
│   ├── guard.py                Auth — JWT + session-cookie authentication
│   ├── tokens.py                ApiTokenAuth — Sanctum-style API tokens
│   └── authorization.py         Policy, authorize, current_user, @role/@permission
├── cache/                    optional — Redis driver needs the `cache` extra
│   ├── drivers.py             Memory/File/Redis cache drivers
│   └── cache.py                 Cache facade, make_cache(), default_cache()
├── events/                   optional — no extra dependencies
│   └── dispatcher.py           EventDispatcher, Listener, event(), listen()
├── queue/                    optional — Redis driver needs the `queue` extra
│   ├── drivers.py              Sync/Redis queue drivers (BLPOP priority queues)
│   ├── worker.py                 Worker — retries + backoff
│   └── job.py                     Job base class
├── scheduler/                optional — no extra dependencies
│   ├── cron.py                  A standalone 5-field cron expression parser
│   └── schedule.py                Schedule, ScheduledTask
├── mail/                     optional — no extra dependency (stdlib smtplib)
│   ├── drivers.py              Smtp/Array mail drivers
│   └── mailer.py                 Mailer, PendingMail, Mailable
├── notifications/            optional — the mail channel depends on `mail/`
│   ├── channels.py             MailChannel, DatabaseNotificationChannel
│   └── manager.py                NotificationManager, notify()
├── storage/                  optional — S3 driver needs the `storage` extra
│   └── drivers.py               Local (path-traversal-checked) and S3 drivers
├── tenancy/                  optional — no extra dependencies
│   ├── model.py                 TenantScopedMixin (shared DB, tenant_id column)
│   ├── database.py               TenantDatabaseManager (database per tenant)
│   └── middleware.py              TenantResolutionMiddleware + resolvers
└── console/
    ├── cli.py             Typer app + third-party command discovery
    ├── naming.py           PascalCase/snake_case/kebab-case helpers for generators
    ├── generator.py        Jinja2-based stub rendering + project scaffolding
    ├── commands/           new, init, serve, route:list, make:*, migrate:*, db:seed,
    │                        cache:clear, config:clear, queue:work, schedule:run,
    │                        package:install
    └── stubs/              Templates for `make:*` and `pyforge new`
```

Each module is independently importable and has a narrow, single
responsibility — there is no module that both defines DI bindings *and*
does HTTP routing, for instance. This is what keeps `container/` reusable
outside of a PyForge app entirely, if someone wants just the DI pattern.
`database/` and `orm/` are split the same way: `database/` knows about
connections, sessions, and raw schema DDL; `orm/` knows about `Model` and
query building and depends on `database/` for a session, never the other
way around. `auth/`, `cache/`, `events/`, `queue/`, `scheduler/`, `mail/`,
`notifications/`, and `storage/` are all opt-in the same way: nothing under
`pyforge/__init__.py`'s import chain touches any of them, so a plain
`pip install pyforge-framework` never pulls in `bcrypt`, `pyjwt`, `redis`,
or `boto3` for an app that doesn't use the corresponding module.
`notifications/` is the one exception to "optional modules don't depend on
each other" — its mail channel imports `pyforge.mail` deliberately, since a
notification's mail channel is just a router over the mail system rather
than a duplicate mail-sending implementation.

## Planned modules (Phase 7+, not yet present)

`testing/` (test helpers beyond what pytest+httpx already give you — see
[07-testing-architecture.md](07-testing-architecture.md)) and `websocket/`
(a broadcasting abstraction on top of FastAPI's native WebSocket support).
See [09-roadmap.md](09-roadmap.md) for sequencing.

## Dependency direction

```
console/  →  everything (it generates and inspects code that uses the rest)
orm/      →  database/
routing/  →  container/, middleware/
core/     →  container/, config/, providers/, routing/, middleware/, database/
container/, config/, providers/, middleware/, database/ → (nothing internal)
```

`container/`, `config/`, `providers/`, `middleware/`, and `database/` never
import from `core/` or `routing/` — they're usable standalone (e.g.
`database/` + `orm/` work with a bare `DatabaseManager`, no `PyForge` app
required — every `tests/test_orm.py` test does exactly that). This is
enforced by convention today (the module count is still small enough to
review by eye); a lint rule (e.g. an `import-linter` contract) is planned
once that stops being true.

The optional packages (`auth/`, `cache/`, `events/`, `queue/`, `scheduler/`,
`mail/`, `notifications/`, `storage/`, `tenancy/`) all point one direction —
into core — never the reverse. `pyforge.tenancy` needed core to expose one
new, narrow seam (`DatabaseManagerLike`, a `Protocol` in `database/manager.py`
capturing exactly the three methods `session_scope()` calls) to plug
`TenantDatabaseManager` into `set_current_database()` without subclassing
`DatabaseManager` or core importing tenancy. That is the intended shape for
every future case like it: a real package hits a real limit, core grows the
smallest structural seam that fixes it, and the dependency arrow never flips.
