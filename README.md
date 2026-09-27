# PyForge

**A batteries-included web framework for Python — built on FastAPI.**

PyForge gives you an elegant project structure, a capable CLI, routing,
controllers, a DI container, and service providers out of the box, while
FastAPI stays the real HTTP engine underneath — always one attribute away
(`app.fastapi`), never hidden.

> **Status:** `0.7.0`, all 7 phases of the roadmap complete. The foundation,
> the database layer, the API layer, authentication/authorization,
> application infrastructure (cache, events, queue, scheduler, mail,
> notifications, storage), multi-tenancy, and production-readiness (test
> helpers, security hardening, a Docker image, an end-user docs site, full
> CI) are implemented and tested today. Still pre-`1.0.0` on purpose — see
> [the roadmap](docs/architecture/09-roadmap.md#phase-7--production-readiness--070-except-where-noted)
> for why finishing the checklist isn't the same as an API-stability
> promise, and for exactly what's real versus what's deliberately deferred
> (PyPI publication is the one item left).

**Full documentation:** the guides in [`docs-site/`](docs-site/) cover
everything below in task-oriented detail — run `mkdocs serve` from that
directory (after `pip install -r docs-site/requirements.txt`) to browse them
locally, including a [Troubleshooting](docs-site/docs/troubleshooting.md)
page for the gotchas that actually trip people up.

```bash
pip install pyforge-framework
pyforge new blog
cd blog
pyforge serve
```

Visit `http://localhost:8000/` for a welcome message, or
`http://localhost:8000/docs` for FastAPI's interactive API docs — generated
automatically, for free.

## Why PyForge

FastAPI is an excellent HTTP layer with a thin story around everything
*around* the HTTP layer: how you structure a growing app, wire dependencies,
organize config, or generate boilerplate. PyForge answers those questions
directly, in idiomatic, typed, async Python — a real project structure, a DI
container, service providers, and a code generator, built as proper Python
architecture rather than borrowed wholesale from another language's
framework. See [docs/architecture/01-framework-architecture.md](docs/architecture/01-framework-architecture.md)
for what that means concretely.

## A quick tour of what works today

**Routing + controllers**, resolved through a DI container:

```python
# routes/api.py
from pyforge import Router
from app.controllers.user_controller import UserController

router = Router()
router.get("/users/{id}", UserController.show, name="users.show")

with router.group(prefix="/admin", middleware=["auth"]) as group:
    group.get("/stats", AdminController.stats)
```

**Plain FastAPI, unmodified, whenever you want it:**

```python
from pyforge import PyForge

app = PyForge()

@app.get("/hello")
async def hello():
    return {"message": "Hello"}

app.fastapi.add_middleware(SomeStarletteMiddleware)
```

**Dependency injection with autowiring:**

```python
from pyforge import container

class CheckoutService:
    def __init__(self, gateway: PaymentGateway) -> None:
        self.gateway = gateway

container.bind(PaymentGateway, StripeGateway)
service = container.make(CheckoutService)  # gateway resolved automatically
```

**Config from `.env` + `config/*.py`:**

```python
from pyforge import config, env

# config/app.py
config = {"name": env("APP_NAME", "My App")}

# anywhere:
config("app.name")
```

**Service providers**, for packaging bindings/routes/config:

```python
from pyforge import ServiceProvider

class PaymentServiceProvider(ServiceProvider):
    def register(self) -> None:
        self.app.container.singleton(PaymentGateway, StripeGateway)

app.register(PaymentServiceProvider)
```

**An Active-Record `Model`, query builder, and migrations** — with the
database session wired into every request automatically, zero boilerplate:

```python
class Post(TimestampsMixin, Model):
    __tablename__ = "posts"
    title: Mapped[str] = mapped_column(String(255))

class PostController:
    async def index(self) -> list[dict]:
        page = Post.query().order_by("created_at", "desc").paginate(per_page=20)
        return page.to_dict()

    async def store(self, title: str) -> dict:
        post = Post.create(title=title)
        return {"id": post.id, "title": post.title}
```

```bash
pyforge make:model Post --migration   # app/models/post.py + a migration
pyforge migrate                       # apply it
pyforge db:seed                       # run database/seeders/database_seeder.py
```

**Authentication & authorization** (optional: `pip install pyforge-framework[auth]`):

```python
from pyforge.auth import Auth, current_user, role

class AuthController:
    def __init__(self, auth: Auth) -> None:  # autowired via the container
        self.auth = auth

    async def login(self, request: LoginRequest) -> dict:
        user = self.auth.attempt(request.email, request.password)
        return self.auth.login(user)  # {"access_token", "refresh_token", ...}

class ProfileController:
    async def me(self, user: Any = Depends(current_user)) -> dict:
        return {"id": user.id}

class AdminController:
    @role("admin")
    async def stats(self) -> dict: ...
```

**Cache, queue, mail, notifications, storage** — each independent and optional:

```python
from pyforge.cache import default_cache
from pyforge.queue import dispatch
from pyforge.mail import mail
from pyforge.notifications import notify
from pyforge.storage import default_storage

default_cache().remember("users:1", 300, lambda: User.find(1))
dispatch(SendWelcomeEmail(user.id))
mail().to(user.email).send(WelcomeEmail(user))
notify(user, WelcomeNotification())
default_storage().put("avatars/photo.jpg", file_bytes)
```

**Multi-tenancy** (optional, no extra dependency):

```python
from pyforge.tenancy import TenantScopedMixin, TenantResolutionMiddleware, subdomain_tenant_resolver

class Post(TenantScopedMixin, Model):   # shared database, tenant_id column
    __tablename__ = "posts"

app.use_middleware(TenantResolutionMiddleware, resolver=subdomain_tenant_resolver)

Post.all()               # scoped to the current tenant — no cross-tenant leaks
Post.create(title="Hi")  # tenant_id stamped in automatically
```

**Testing helpers** (`pyforge.testing`) — fake the side effects, assert on them:

```python
from pyforge.testing import fake_queue, fake_events, assert_status

def test_registration_dispatches_a_welcome_email():
    queue = fake_queue()
    response = client.post("/register", json={"email": "ada@example.com"})
    assert_status(response, 201)
    queue.assert_pushed(SendWelcomeEmail)
```

**Security** (`pyforge.security`) — rate limiting and secure headers, no extra dependency:

```python
from pyforge.security import rate_limit, SecurityHeadersMiddleware

class AuthController:
    @rate_limit("5/minute")
    async def login(self, request: LoginRequest) -> dict: ...

app.use_middleware(SecurityHeadersMiddleware)
```

Every generated project also ships a `Dockerfile` — see
[docs/architecture/11-deployment.md](docs/architecture/11-deployment.md).

Every one of these is backed by a passing test in [`tests/`](tests/) and
exercised for real by the generated project template in
[`src/pyforge/console/stubs/`](src/pyforge/console/stubs/) — nothing above
is aspirational.

## CLI

```bash
pyforge new blog                    # scaffold a new project
pyforge init                        # scaffold into the current directory
pyforge serve                       # run the dev server
pyforge route:list                  # list every registered route
pyforge make:controller User        # app/controllers/user_controller.py
pyforge make:middleware Auth        # app/middleware/auth.py
pyforge make:provider Payment       # app/providers/payment_service_provider.py
pyforge make:command ImportUsers    # app/commands/import_users.py
pyforge make:model Post -m          # app/models/post.py + a migration
pyforge migrate                     # apply pending migrations
pyforge migrate:rollback            # undo the last one
pyforge db:seed                     # run database/seeders/database_seeder.py
pyforge make:policy Post            # app/policies/post_policy.py
pyforge cache:clear                 # flush the configured cache
pyforge queue:work --queue=high,default
pyforge schedule:run                # runs due tasks from app/schedule.py, meant for cron
pyforge make:job SendWelcomeEmail   # app/jobs/send_welcome_email.py
pyforge package:install auth        # pip install pyforge-framework[auth]
```

Full reference: [docs/architecture/04-cli-specification.md](docs/architecture/04-cli-specification.md).
The CLI is extensible by third-party packages via a Python entry-point group
— see [docs/architecture/05-plugin-package-architecture.md](docs/architecture/05-plugin-package-architecture.md).

## Documentation

- [Framework architecture](docs/architecture/01-framework-architecture.md) — vision, philosophy, layering
- [Core package architecture](docs/architecture/02-core-package-architecture.md) — what's core vs. optional, and why
- [Public API design](docs/architecture/03-public-api-design.md) — every public symbol, with examples
- [CLI specification](docs/architecture/04-cli-specification.md)
- [Plugin/package architecture](docs/architecture/05-plugin-package-architecture.md)
- [Database architecture](docs/architecture/06-database-architecture.md) — ORM, query builder, migrations
- [Testing architecture](docs/architecture/07-testing-architecture.md)
- [Documentation architecture](docs/architecture/08-documentation-architecture.md)
- [Roadmap](docs/architecture/09-roadmap.md) — what's built vs. planned, phase by phase
- [Security](docs/architecture/10-security.md) — a checklist-driven review of what PyForge does and doesn't do
- [Deployment](docs/architecture/11-deployment.md) — the generated Docker image, env config, platform recipes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every public API needs a test and a
docs entry — see [the docs-as-code rules](docs/architecture/08-documentation-architecture.md#docs-as-code-rules).

## Security

See [SECURITY.md](SECURITY.md) for how to report a vulnerability.

## License

[MIT](LICENSE).
