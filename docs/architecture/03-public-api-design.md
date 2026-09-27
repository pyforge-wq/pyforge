# Public API Design

Everything below is implemented and covered by tests in `tests/`. Import
paths shown are all re-exported from the top-level `pyforge` package unless
noted otherwise.

## `PyForge` — the application

```python
from pyforge import PyForge

app = PyForge(base_path=".", title="My App")
```

| Member | Signature | Notes |
|---|---|---|
| `base_path` | `Path` | Defaults to `Path.cwd()`. Where `.env` and `config/` are loaded from. |
| `container` | `Container` | The app's DI container (defaults to the process-wide default). |
| `config` | `Config` | Loaded from `config/*.py` under `base_path`. |
| `middleware` | `MiddlewareRegistry` | Register named route-guard dependencies. |
| `fastapi` / `fastapi_app` | `property -> FastAPI` | The real, underlying FastAPI instance. Two names for the same thing — `fastapi` for brevity, `fastapi_app` to match the spec/README wording. |
| `register_routes(router, *, prefix="", tags=None)` | `-> PyForge` | Mounts a `Router`'s routes onto the app. |
| `use_middleware(cls, **options)` | `-> PyForge` | Passthrough to `FastAPI.add_middleware` for global, ASGI-level middleware (CORS, GZip, ...). |
| `register(provider_class)` | `-> ServiceProvider` | Instantiates the provider, runs `register()` immediately, queues `boot()` for startup. |
| `boot()` | `-> None` | Runs pending providers' `boot()`. Called automatically on FastAPI startup; safe to call again (idempotent). |
| `make(abstract, **params)` | `-> Any` | Shorthand for `app.container.make(...)`. |
| `get/post/put/patch/delete/options/head/websocket(path, **kwargs)` | decorators | Passthrough to the equivalent `FastAPI` decorator — `@app.get("/hello")` works exactly like plain FastAPI. |
| `__call__(scope, receive, send)` | ASGI | `PyForge` itself is ASGI-callable — `uvicorn main:app` works without reaching into `.fastapi`. |

### FastAPI interop

Nothing about PyForge prevents using FastAPI directly:

```python
from fastapi import Depends, BackgroundTasks
from fastapi.responses import JSONResponse

@app.get("/hello")
async def hello():
    return {"message": "Hello"}

app.fastapi.add_exception_handler(ValueError, my_handler)
```

Any FastAPI middleware, dependency, sub-router, or response class is usable
unmodified, because `app.fastapi` is a real `fastapi.FastAPI` — not a
lookalike.

## Routing

```python
from pyforge import Router

router = Router()

router.get("/users", UserController.index)
router.post("/users", UserController.store)
router.get("/users/{id}", UserController.show, name="users.show")

with router.group(prefix="/api/v1", middleware=["auth"], name="v1") as group:
    group.get("/me", ProfileController.show, name="me")
    # -> registered as "v1.me", path "/api/v1/me"
```

- **Plain functions** are registered exactly as FastAPI would — no wrapping,
  full native parameter/dependency inference.
- **Controller actions** — an unbound method reference like
  `UserController.show` — are detected automatically (by inspecting
  `__qualname__` and the first parameter being `self`) and wrapped so a
  fresh controller instance is resolved from the `Container` on every
  request, while the wrapped endpoint's signature is rewritten to drop
  `self`. FastAPI never sees `self`; path params, bodies, and `Depends()` on
  the *rest* of the method signature work exactly as they would on a plain
  function.
- **Route groups** (`router.group(...)`) are a context manager: routes
  registered on the yielded `Router` are mounted onto the parent via
  `include_router()` when the `with` block exits, with `prefix`,
  `middleware`-derived `dependencies`, and `tags` applied. Named routes get
  an optional dotted name prefix (`name="v1"` + `name="me"` → `"v1.me"`).
- **`router.url(route_name, **params)`** reverses a named route back to a
  path: `router.url("v1.me")` → `"/api/v1/me"`.
- Controllers themselves are plain classes — no base class required:

  ```python
  class UserController:
      async def index(self) -> list[dict]:
          ...
      async def show(self, id: int) -> dict:
          ...
  ```

  Route-model binding (resolving `id: int` straight to a `User` instance
  automatically) isn't implemented yet even though the ORM now exists — see
  [09-roadmap.md](09-roadmap.md); today a controller calls
  `User.find_or_fail(id)` itself.

## `Container` — dependency injection

```python
from pyforge import Container, container  # container = the process-wide default

container.bind(PaymentGateway, StripeGateway)          # transient
container.singleton(Cache, RedisCache)                 # shared
container.instance(Settings, Settings(debug=True))      # pre-built object

class CheckoutService:
    def __init__(self, gateway: PaymentGateway) -> None:
        self.gateway = gateway

service = container.make(CheckoutService)  # gateway autowired
```

Anything not explicitly bound is **autowired**: the container inspects
`__init__`'s type hints and resolves each parameter recursively, falling
back to the parameter's default if present, and raising
`BindingResolutionError` if a required parameter has neither a binding nor a
default. `container.call(fn, **overrides)` does the same resolution for a
plain callable, useful for one-off invocations.

A fresh `Container()` can always be constructed for test isolation instead
of using the shared default — every framework class that touches the
container (`PyForge`, `Router`) accepts one via `container=...`.

## `ServiceProvider`

```python
from pyforge import ServiceProvider

class PaymentServiceProvider(ServiceProvider):
    def register(self) -> None:
        self.app.container.bind(PaymentGateway, StripeGateway)

    def boot(self) -> None:
        self.app.middleware.register("verified-webhook", verify_stripe_signature)

app.register(PaymentServiceProvider)
```

`register()` runs immediately (must not depend on other providers).
`boot()` runs once, for every registered provider, on FastAPI startup — safe
to depend on bindings any other provider registered.

## Configuration

```python
from pyforge import config, env

# config/app.py:
config = {"name": env("APP_NAME", "My App"), "debug": env("APP_DEBUG", False)}

# anywhere after a PyForge() app has been constructed:
config("app.name")          # -> "My App"
config("app.missing", 42)   # -> 42 (default)
```

`env(key, default)` reads `os.environ`, casting `"true"/"false"/"null"` and
numeric strings to their real Python types. `.env` is loaded via
`load_env()` on `PyForge()` construction, without overriding variables
already set in the real process environment (so `APP_ENV=production
uvicorn ...` always wins over a stray `.env`).

`config()` is a global helper backed by whichever `PyForge` app was
constructed most recently in the process — fine for the common single-app
case; multi-app-per-process code should use `app.config` directly instead.

## Database & ORM

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from pyforge import Model, TimestampsMixin, has_many, belongs_to

class Author(TimestampsMixin, Model):
    __tablename__ = "authors"
    name: Mapped[str] = mapped_column(String(255))
    books: Mapped[list["Book"]] = has_many("Book", back_populates="author")

Author.all()
Author.find(1)
Author.where("name", "Ada Lovelace").first()
Author.create(name="Ada Lovelace")
Author.query().with_("books").paginate(per_page=20, page=1)
```

| Member | Notes |
|---|---|
| `Model` | Active-Record base (`all`, `find`, `find_or_fail`, `where`, `create`, `query`; instance `save`/`update`/`delete`). Integer auto-increment primary key by default. |
| `UUIDModel`, `ULIDModel` | Same API, UUID or ULID primary key — a base class choice, not a mixin (see [06-database-architecture.md](06-database-architecture.md)). |
| `QueryBuilder` | Returned by `.query()`/`.where(...)`; chainable (`where`, `or_where`, `where_in`, `where_null`, `where_between`, `order_by`, `group_by`, `having`, `join`, `left_join`, `select`, `limit`, `offset`, `with_`), terminal (`get`, `first`, `find`, `count`, `exists`, `paginate`). `.statement` is a real SQLAlchemy `Select`. |
| `Paginator` | Returned by `.paginate(per_page, page)`: `.data`, `.current_page`, `.per_page`, `.total`, `.last_page`, `.to_dict()`. |
| `TimestampsMixin`, `SoftDeletesMixin` | Opt-in mixins — `created_at`/`updated_at` kept in sync automatically; soft-deleted rows excluded from queries by default (`Model.query(with_trashed=True)` to include them). |
| `has_one`, `has_many`, `belongs_to`, `belongs_to_many` | Thin, named wrappers over SQLAlchemy's `relationship()`. |
| `Factory` | `UserFactory.create()`, `.create_batch(n)`, `.make()` (no persist); `UserFactory().state(...).create()` for one-off overrides; a subclass adds its own named traits (`def admin(self): return self.state(role="admin")`). |
| `Seeder` | `pyforge db:seed` runs `DatabaseSeeder().run()` inside a `session_scope()`. |
| `pyforge.database.Schema` | Migration-time schema builder (`Schema.create`, `Schema.table`, `Schema.drop`) — used inside a migration's `upgrade()`/`downgrade()`, not application code. |

Database access needs zero explicit wiring in a controller — see
[06-database-architecture.md](06-database-architecture.md#1-connection--session-management-pyforgedatabase)
for how the per-request session gets there automatically. The ORM is
**synchronous**, a deliberate choice explained in that same document; the
rest of PyForge stays async-first.

## Validation: `FormRequest`

```python
from pyforge import FormRequest

class CreateUserRequest(FormRequest):
    rules = {
        "name": "required|string|max:255",
        "email": "required|email|unique:users",
        "password": "required|min:8|confirmed",
    }

class UserController:
    async def store(self, request: CreateUserRequest) -> dict:
        return {"created": request.validated()}
```

A controller (or plain function route) parameter annotated with a
`FormRequest` subclass and no explicit default is turned into a FastAPI
dependency automatically by `Router` — no `Depends(...)` needed. On failure
it raises `HTTPException(422, detail={"errors": {field: [messages]}})`
before the handler runs. Supported rules: `required`, `nullable`, `string`,
`integer`, `numeric`, `boolean`, `email`, `url`, `min:N`, `max:N`, `in:a,b,c`,
`confirmed` (compares against `<field>_confirmation`), `unique:table[,column]`
(checked against `pyforge.orm.Base.metadata`'s tables, so it works without
importing the specific `Model` class). Native Pydantic models work exactly
as they always have in FastAPI — `FormRequest` is an alternative, not a
replacement.

## API transformation: `Resource`

```python
from pyforge import Resource

class UserResource(Resource):
    def to_dict(self, user) -> dict:
        return {"id": user.id, "name": user.name}

UserResource.make(user)                                    # -> dict
UserResource.collection(users)                              # -> list[dict]
UserResource.paginated(User.query().paginate(per_page=20))  # -> {"data": [...], "meta": {...}}
```

`paginated(...)` is the direct bridge from `QueryBuilder.paginate(...)`'s
`Paginator` to the `{"data": [...], "meta": {...}}` envelope from the
original spec.

## Exception handling

Every `PyForge` app registers two exception handlers automatically:

| Exception | Response |
|---|---|
| `pyforge.orm.ModelNotFoundError` | `404`, `{"message": str(exc)}` |
| `pyforge.core.PyForgeError` (and subclasses) | `500`, `{"message": str(exc)}` if `config("app.debug")` else `{"message": "Internal Server Error"}` |

Application code can register more via `app.fastapi.add_exception_handler(...)`
or FastAPI's own `@app.exception_handler(...)` — these two are just what
PyForge itself raises.

## Authentication & authorization: `pyforge.auth` (optional)

Not imported by `import pyforge` — install the extra
(`pip install pyforge-framework[auth]`) and import explicitly:

```python
from pyforge.auth import Auth, current_user, role, permission, authorize, Policy

auth = Auth(User, secret=config("auth.jwt.secret"))  # build once, e.g. in a ServiceProvider

class AuthController:
    def __init__(self, auth: Auth) -> None:  # autowired via container.instance(Auth, auth)
        self.auth = auth

    async def register(self, request: RegisterRequest) -> dict:
        user = User.create(email=request.email, password_hash=self.auth.hash_password(request.password))
        return self.auth.login(user)  # {"access_token", "refresh_token", "token_type"}

class ProfileController:
    async def me(self, user: Any = Depends(current_user)) -> dict:
        return {"id": user.id}

class AdminController:
    @role("admin")
    async def stats(self) -> dict: ...
```

| Member | Notes |
|---|---|
| `Auth(user_model, *, secret, ...)` | `.attempt(email, password)`, `.login(user)` (access+refresh pair), `.refresh(token)`, `.required`/`.optional` (bearer-token `Depends`), `.session_login(response, user, *, secure=True)`/`.session_required` (cookie-based session auth — `secure=True` by default, pass `False` for local `http://` dev), `.make_signed_token`/`.verify_signed_token` (email verification / password reset tokens — send the actual email yourself via `pyforge.mail`, e.g. from the controller that calls `make_signed_token`). |
| `hash_password`, `verify_password` | bcrypt-based; also available as `Auth.hash_password`/`Auth.verify_password`. |
| `ApiTokenAuth(token_model, user_model)` | Sanctum-style personal access tokens — `.issue(user)` returns a plaintext token shown once; `.required` is a bearer-token `Depends` checked against the hash in your own token table. |
| `current_user` | A `Depends(current_user)` resolving whichever `Auth` was registered via `set_default_auth(...)`, looked up fresh per request — use this (not `Depends(auth.required)`) when the controller has no other reason to hold a specific `Auth` instance, so import order relative to `set_default_auth(...)` never matters. |
| `role(name)`, `permission(name)` | Decorators for a controller action; 403 unless the resolved user's `.role` matches / `.has_permission(name)` returns true. Default to `current_user`'s registered default auth; pass `get_user=` for an explicit one. |
| `Policy`, `authorize(policy, action, user, *args)` | Plain policy objects (`def update(self, user, model) -> bool`); `authorize(...)` 403s if the method returns falsy. |

**Import-order gotcha:** a decorator like `@role("admin")` resolves its
dependency at class-*definition* time (when the module is imported), not
per-request — so `set_default_auth(...)` (typically in a service provider's
`register()`) must run before any module that uses the bare decorator form
is imported. The generated project's `main.py` registers providers before
importing `routes/` for exactly this reason. `current_user` sidesteps this
entirely by resolving `default_auth()` at request time instead.

## Application infrastructure (optional): cache, events, queue, scheduler, mail, notifications, storage

Seven independent, opt-in modules — none imported by `import pyforge`, and
none imported by each other except `pyforge.notifications`' mail channel,
which uses `pyforge.mail` deliberately (a notification's mail channel is
just a router over the mail system, not a duplicate implementation). Each
follows the same shape: a `make_x(config)` factory reading the matching
`config/x.py`, plus
`set_default_x(...)`/`default_x()` for the process-wide instance a service
provider registers once.

### Cache (`pyforge.cache`)

```python
from pyforge.cache import make_cache, set_default_cache, default_cache

set_default_cache(make_cache(config("cache")))   # in a service provider
default_cache().remember("users:1", 300, lambda: User.find(1))
```

`Cache.get`/`.put`/`.forget`/`.remember`/`.flush`. Drivers: `MemoryCacheDriver`
(default, in-process), `FileCacheDriver` (pickled files, survives a restart),
`RedisCacheDriver` (needs `pip install pyforge-framework[cache]`; `.flush()`
runs `FLUSHDB` — use a dedicated Redis DB index for the cache). `pyforge cache:clear`.

### Events (`pyforge.events`)

```python
from pyforge.events import event, listen, Listener

class SendWelcomeEmail(Listener):
    async def handle(self, evt: UserRegistered) -> None: ...

listen(UserRegistered, SendWelcomeEmail)   # in a service provider's boot()
await event(UserRegistered(user))          # await — see the note below
```

`event(...)` is **`await`-able**, not the sync-looking call in the original
spec — the same kind of deliberate, documented deviation as the ORM being
sync instead of matching a literal async example, just in the opposite
direction: dispatch always happens from already-`async def` code, and some
listeners are legitimately `async def` too, so this is the honest shape
rather than reaching for `asyncio.run()` (which breaks inside an
already-running event loop). Both sync and async `handle()` methods work.

### Queue / jobs (`pyforge.queue`)

```python
from pyforge.queue import Job, dispatch, make_queue, set_default_queue

class SendWelcomeEmail(Job):
    max_retries = 2
    retry_backoff_seconds = 5
    def __init__(self, user_id: int) -> None: self.user_id = user_id
    def handle(self) -> None: ...

set_default_queue(make_queue(config("queue")))   # in a service provider
dispatch(SendWelcomeEmail(user.id))
```

`SyncQueueDriver` (default — runs jobs immediately, nothing to work through)
and `RedisQueueDriver` (needs the `queue` extra; `BLPOP` across queue names
in priority order, e.g. `pyforge queue:work --queue=high,default`). A `Job`
must be picklable, and its attributes are captured **by value** at dispatch
time — it can't report results back via shared mutable state; write results
to the database instead. `Worker` retries up to `max_retries` times
(sleeping `retry_backoff_seconds` between attempts) before calling
`on_failure`. No job-timeout enforcement (see [09-roadmap.md](09-roadmap.md)).

### Scheduler (`pyforge.scheduler`)

```python
from pyforge.scheduler import Schedule

schedule = Schedule()   # app/schedule.py
schedule.every_day(GenerateReports()).at("02:00")
schedule.every_hour(CleanupTemporaryFiles())
schedule.cron("*/15 * * * *", SyncExternalData())
```

`pyforge schedule:run` runs every currently-due task once and exits — meant
to be invoked by a real OS cron entry every minute, the same model as any
cron-driven scheduler; there's no persisted "last run" state, since the once-a-minute
external cadence plus each task's own time check is sufficient. A "job" here
just needs a `handle()` method or to be callable.

### Mail (`pyforge.mail`)

```python
from pyforge.mail import Mailable, make_mailer, set_default_mailer, mail

class WelcomeEmail(Mailable):
    def __init__(self, user): self.user = user
    def subject(self) -> str: return "Welcome!"
    def html(self) -> str: return f"<p>Welcome, {self.user.name}!</p>"

set_default_mailer(make_mailer(config("mail")))   # in a service provider
mail().to(user.email).send(WelcomeEmail(user))
```

`SmtpMailDriver` (stdlib `smtplib`, no extra dependency) and `ArrayMailDriver`
(captures sent messages in `.sent` — the testing driver, `config = {"default": "array"}`).
No SES/Mailgun/Postmark/SendGrid adapters yet — each is a distinct HTTP API,
not an SMTP variant.

### Notifications (`pyforge.notifications`)

```python
from pyforge.notifications import Notification, notify, register_channel, DatabaseNotificationChannel

class WelcomeNotification(Notification):
    def via(self, notifiable) -> list[str]: return ["mail", "database"]
    def to_mail(self, notifiable) -> Mailable: return WelcomeEmail(notifiable)
    def to_database(self, notifiable) -> dict: return {"message": "Welcome!"}

register_channel("database", DatabaseNotificationChannel(YourNotificationModel))
notify(user, WelcomeNotification())
```

`"mail"` is registered by default; `"database"` needs your own model (same
reasoning as `ApiTokenAuth` — the table shape is an app decision, not fixed
by the framework).

### Storage (`pyforge.storage`)

```python
from pyforge.storage import make_storage, set_default_storage, default_storage

set_default_storage(make_storage(config("storage")))   # in a service provider
default_storage().put("avatars/photo.jpg", file_bytes)
default_storage().url("avatars/photo.jpg")
```

`LocalStorageDriver` (default; rejects paths that escape its root) and
`S3StorageDriver` (needs the `storage` extra — also covers R2 and other
S3-compatible stores via `endpoint_url` + a custom `base_url`). No Azure
Blob/GCS drivers yet.

## Multi-tenancy (optional): `pyforge.tenancy`

Two independent strategies — pick one, or combine them:

```python
from pyforge.tenancy import TenantScopedMixin, TenantResolutionMiddleware, subdomain_tenant_resolver

class Post(TenantScopedMixin, Model):   # shared database, tenant_id column
    __tablename__ = "posts"
    title: Mapped[str] = mapped_column(String(255))

app.use_middleware(TenantResolutionMiddleware, resolver=subdomain_tenant_resolver)

Post.all()               # scoped to the current request's tenant automatically
Post.create(title="Hi")  # tenant_id stamped in automatically
```

`TenantScopedMixin` overrides `Model.query()`/`.create()` (everything else —
`.all()`, `.find()`, `.where()` — goes through `query()`, so they're scoped
for free): with a current tenant set, every read/write through it is
confined to that tenant; with none set, it's unscoped. This is the
"prevent accidental cross-tenant queries" guarantee from the original spec —
there's deliberately no per-call escape hatch to see another tenant's rows.

```python
from pyforge.tenancy import TenantDatabaseManager, set_current_database

def connection_for_tenant(tenant_id: str) -> dict:
    return {"driver": "mysql", "database": f"tenant_{tenant_id}", ...}

set_current_database(TenantDatabaseManager(connection_for_tenant=connection_for_tenant))
```

`TenantDatabaseManager` (database-per-tenant) duck-types
`pyforge.database`'s `DatabaseManagerLike` protocol and routes
`session_scope()` to a distinct, lazily-built `DatabaseManager` per tenant —
a drop-in replacement for `set_current_database(...)`, so `Model` and every
other database-touching call works unmodified.

Both strategies read the current tenant from the same place:
`current_tenant_id()`/`current_tenant_id_or_none()`, set by `tenant_scope(...)`
or `TenantResolutionMiddleware` (with `subdomain_tenant_resolver` or
`header_tenant_resolver(...)`, or your own resolver function).

## Security (optional): `pyforge.security`

```python
from pyforge.security import rate_limit, SecurityHeadersMiddleware

app.use_middleware(SecurityHeadersMiddleware)  # X-Frame-Options, HSTS, ...

class LoginController:
    @rate_limit("5/minute")
    async def attempt(self, request: LoginRequest) -> dict: ...
```

`rate_limit(rate, *, key_func=None, cache=None)` 429s past the given count
per window (default key: client IP; default cache: `pyforge.cache.default_cache()`).
`SecurityHeadersMiddleware` sets a sane default header set without
overriding anything your own code already set. See
[10-security.md](10-security.md) for the full picture — what's covered,
what isn't, and two real findings (a tenant-isolation gap and a
secure-cookie default) fixed during a review while building this phase.

## Four levels of usage

| Level | Example | What's happening |
|---|---|---|
| Beginner | `User.create(...)` / `router.get("/users", UserController.index)` | Convention: container-resolved controllers, an Active-Record `Model`, no manual wiring. |
| Intermediate | `User.query().where(...).paginate(...)` / `with router.group(middleware=["auth"]) as g: g.get(...)` | Explicit query building/grouping, still declarative. |
| Advanced | `container.make(CheckoutService)` / a real `sqlalchemy.orm.Session` via `current_session()` | Direct container/SQLAlchemy use, custom bindings, interface→implementation swaps. |
| FastAPI expert | `app.fastapi.add_middleware(...)`, `@app.get(...)`, `Depends(...)`, raw `session.execute(...)` | Drop to FastAPI/Starlette/SQLAlchemy directly; nothing is hidden. |

This table will grow a row per phase (e.g. Phase 7 adds test-helper conveniences).

## Stability note

Everything documented here is `0.6.0` and pre-`1.0` — expect the *shapes* to
stay stable (this is the intended long-term API) but signatures may still
gain optional parameters as later phases land. See
[09-roadmap.md](09-roadmap.md).
