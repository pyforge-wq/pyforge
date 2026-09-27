# Dependency Injection, Configuration & Service Providers

## The container

```python
from pyforge import Container, container  # container = the process-wide default

container.bind(PaymentGateway, StripeGateway)           # transient — new instance per resolve
container.singleton(Cache, RedisCache)                  # shared — built once, reused
container.instance(Settings, Settings(debug=True))      # a pre-built object, used as-is

class CheckoutService:
    def __init__(self, gateway: PaymentGateway) -> None:
        self.gateway = gateway

service = container.make(CheckoutService)  # gateway autowired
```

Anything not explicitly bound is **autowired**: the container inspects
`__init__`'s type hints and resolves each parameter recursively, falling
back to the parameter's default if present, and raising
`BindingResolutionError` if a required parameter has neither a binding nor a
default.

```python
container.call(some_function, extra_kwarg="value")  # same resolution, for a plain callable
```

Controllers go through this automatically — a controller's `__init__`
parameters are autowired the same way, so `UserController(users:
UserRepository)` gets a real `UserRepository` on every request without a
single `Depends(...)` anywhere in the controller.

### Test isolation

A fresh `Container()` can always be constructed instead of using the shared
default — every framework class that touches the container (`PyForge`,
`Router`) accepts one via `container=...`:

```python
def test_checkout_uses_the_fake_gateway():
    test_container = Container()
    test_container.instance(PaymentGateway, FakeGateway())
    service = test_container.make(CheckoutService)
    ...
```

## Service providers

The place to register bindings, config, and routes for a feature:

```python
from pyforge import ServiceProvider

class PaymentServiceProvider(ServiceProvider):
    def register(self) -> None:
        self.app.container.bind(PaymentGateway, StripeGateway)

    def boot(self) -> None:
        self.app.middleware.register("verified-webhook", verify_stripe_signature)

app.register(PaymentServiceProvider)
```

- `register()` runs **immediately** when `app.register(...)` is called — it
  must not depend on bindings any other provider registers, since ordering
  isn't guaranteed at this phase.
- `boot()` runs once, for every registered provider, on FastAPI startup — by
  then every provider's `register()` has already run, so it's safe to depend
  on bindings any other provider set up.

Generate one:

```bash
pyforge make:provider Payment
```

!!! warning "Import order matters for auth decorators"
    If a service provider calls `set_default_auth(...)` (see
    [Authentication](authentication.md)), it must run — and its `register()`
    must have executed — **before** any module using a bare `@role(...)` /
    `@permission(...)` decorator is imported, because those decorators
    resolve their dependency at class-*definition* time. The generated
    project's `main.py` registers providers before importing `routes/` for
    exactly this reason.

## Configuration

```python
# config/app.py
config = {"name": env("APP_NAME", "My App"), "debug": env("APP_DEBUG", False)}
```

```python
from pyforge import config, env

config("app.name")          # -> "My App"
config("app.missing", 42)   # -> 42 (default)
```

Every file under `config/` is a namespace: `config/app.py`'s `config` dict is
read as `config("app.<key>")`, `config/database.py`'s as
`config("database.<key>")`, and so on.

`env(key, default)` reads `os.environ`, casting `"true"`/`"false"`/`"null"`
and numeric strings to their real Python types automatically. `.env` is loaded
automatically when a `PyForge()` app is constructed, **without** overriding
variables already set in the real process environment — so
`APP_ENV=production uvicorn ...` always wins over a stray `.env` file left
on a server.

`config()` as a bare function is a global helper backed by whichever
`PyForge` app was constructed most recently in the process — fine for the
common single-app-per-process case. Code that constructs multiple `PyForge`
apps in one process should use `app.config` directly instead of the global
helper.

## Where config values usually come from

Every generated project ships:

```
config/
├── app.py         APP_NAME, APP_DEBUG, APP_ENV
├── database.py    connections dict, keyed by name
├── auth.py        JWT_SECRET, token TTLs (needs pyforge.auth)
├── cache.py       driver selection (memory/file/redis)
├── mail.py        SMTP settings or "array" for tests
├── queue.py       driver selection (sync/redis)
└── storage.py     local path or S3 bucket/credentials
```

Each of these feeds a `make_x(config("x"))` factory in the matching optional
module — see that module's own guide (e.g. [Storage & Cache](storage-and-cache.md))
for what each namespace's keys mean.
