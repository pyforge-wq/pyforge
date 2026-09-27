# Getting Started

## Requirements

- Python 3.11+
- A way to install packages (`pip`, ideally inside a virtual environment)

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install pyforge-framework
```

## Create a project

```bash
pyforge new blog
cd blog
```

`pyforge new` scaffolds a complete, working project:

```
blog/
├── app/
│   ├── controllers/        welcome_controller.py (demo) + your controllers
│   ├── models/  schemas/  services/  repositories/
│   ├── middleware/  requests/  resources/  policies/
│   ├── events/  listeners/  jobs/  notifications/  commands/
│   ├── providers/           app_service_provider.py (demo, registered in main.py)
│   └── schedule.py
├── routes/
│   ├── api.py               mounted at /api
│   └── web.py                mounted at /
├── config/
│   └── app.py database.py auth.py cache.py mail.py queue.py storage.py
├── database/
│   ├── migrations/          env.py, script.py.mako, versions/
│   └── seeders/             database_seeder.py
├── tests/
│   └── test_welcome.py      a real, passing test against the generated app
├── storage/
├── .env  .env.example
├── pyproject.toml
├── Dockerfile  .dockerignore
└── main.py                   constructs PyForge(), registers routes/providers
```

`pyforge new` also generates a real, random `JWT_SECRET` into `.env` —
never a static placeholder you could accidentally ship to production.

!!! tip "Scaffolding into an existing directory"
    `pyforge init` does the same scaffolding into the **current** directory
    instead of creating a new one — useful if you already made the directory
    and `cd`'d into it. It fails if the directory isn't empty.

## Run it

```bash
pyforge serve
```

This runs the project with `uvicorn`, hot-reload on, at `http://127.0.0.1:8000`
by default. Visit:

- `http://localhost:8000/` — a welcome JSON message
- `http://localhost:8000/docs` — FastAPI's interactive Swagger UI, generated
  automatically from your routes

`pyforge serve` is equivalent to `uvicorn main:app --reload`, but it locates
the project root for you regardless of how `pyforge` itself was installed.

## Run the tests

Every generated project ships a real, passing test out of the box:

```bash
pytest
```

## Add your first real endpoint

Open `routes/api.py` and add a route:

```python
# routes/api.py
from pyforge import Router
from app.controllers.welcome_controller import WelcomeController

router = Router()
router.get("/", WelcomeController.index)
router.get("/ping", lambda: {"pong": True})
```

Or generate a real controller:

```bash
pyforge make:controller Post
```

```python
# app/controllers/post_controller.py
class PostController:
    async def index(self) -> list[dict]:
        return [{"id": 1, "title": "Hello, PyForge"}]
```

```python
# routes/api.py
router.get("/posts", PostController.index)
```

Reload `http://localhost:8000/posts` (or let `--reload` do it for you) and
you'll see the JSON list.

## Add a database-backed model

```bash
pyforge make:model Post --migration
```

This generates `app/models/post.py` and a matching migration. Open the
migration under `database/migrations/versions/` and fill in the columns:

```python
def upgrade() -> None:
    with Schema.create("posts") as table:
        table.id()
        table.string("title")
        table.timestamps()

def downgrade() -> None:
    Schema.drop("posts")
```

Apply it, then use the model — no session wiring required in the controller:

```bash
pyforge migrate
```

```python
# app/models/post.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from pyforge import Model, TimestampsMixin

class Post(TimestampsMixin, Model):
    __tablename__ = "posts"
    title: Mapped[str] = mapped_column(String(255))
```

```python
class PostController:
    async def index(self) -> list[dict]:
        posts = Post.all()
        return [{"id": p.id, "title": p.title} for p in posts]

    async def store(self, title: str) -> dict:
        post = Post.create(title=title)
        return {"id": post.id, "title": post.title}
```

See [Database & ORM](database.md) for the query builder, relationships, and
[Migrations, Factories & Seeders](migrations-and-seeders.md) for the rest of
the schema toolkit.

## Where to go next

- [Routing & Controllers](routing-and-controllers.md) — route groups, named
  routes, middleware
- [Dependency Injection & Config](dependency-injection-and-config.md) —
  autowiring, service providers, `.env`/`config/*.py`
- [Authentication](authentication.md) — JWT, sessions, API tokens (`pip
  install pyforge-framework[auth]`)
- [Deployment](deployment.md) — the `Dockerfile` your project already has
