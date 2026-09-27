# Database & ORM

SQLAlchemy 2.x is the real engine underneath — PyForge wraps it the way
`Router` wraps FastAPI's `APIRouter`: convenience on top, full escape hatch
underneath. MySQL, PostgreSQL, and SQLite all work through the same
SQLAlchemy dialect layer (`pymysql` ships as a core dependency; PostgreSQL
needs `psycopg2`/`psycopg` installed separately).

!!! note "Why the ORM is synchronous"
    The rest of PyForge is async-first, but the ORM deliberately uses plain,
    synchronous SQLAlchemy — not `sqlalchemy.ext.asyncio`. Async SQLAlchemy
    plus Alembic is a real source of friction in practice (lazy-loading a
    relationship inside `async def` code raises `MissingGreenlet` unless
    every access path is eager-loaded or wrapped). A `Model` call from an
    `async def` controller briefly blocks the event loop — a non-issue for
    typical CRUD workloads, and nothing stops you from using a real
    `sqlalchemy.ext.asyncio.AsyncSession` directly for a genuinely
    high-concurrency hot path.

## Defining a model

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from pyforge import Model, TimestampsMixin

class User(TimestampsMixin, Model):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
```

Columns are declared with plain SQLAlchemy 2.0 typed `Mapped[...]`/
`mapped_column(...)` — not a new column DSL (that's reserved for
*migrations*; see [Migrations](migrations-and-seeders.md)).

Or generate the skeleton:

```bash
pyforge make:model User --migration
```

## Zero-wiring database access in controllers

Every HTTP request is automatically wrapped in a database session —
committed on a successful response, rolled back if the handler raises. A
controller needs no `Depends()`, no session parameter:

```python
class UserController:
    async def store(self, name: str) -> dict:
        user = User.create(name=name)
        return {"id": user.id, "name": user.name}
```

Outside a request (scripts, seeders, tests), open a session manually:

```python
from pyforge.database import session_scope

with session_scope():
    User.create(name="Ada")
```

## Active-Record style queries

```python
User.all()
User.find(1)
User.find_or_fail(1)                         # raises ModelNotFoundError -> 404
User.where("email", "ada@example.com").first()
User.where("active", True).get()
user = User.create(name="Ada", email="ada@example.com")
user.name = "Ada Lovelace"
user.save()
user.delete()
```

## The query builder

```python
User.query() \
    .where("active", True) \
    .order_by("created_at", "desc") \
    .paginate(per_page=20, page=1)
```

| Method | Kind | Notes |
|---|---|---|
| `where`, `or_where`, `where_in`, `where_null`, `where_not_null`, `where_between` | chainable | `or_where` combines with the *immediately preceding* condition only — no arbitrary operator-precedence grouping across many conditions |
| `order_by`, `group_by`, `having`, `join`, `left_join`, `select`, `limit`, `offset` | chainable | `having(...)` accepts a raw SQLAlchemy expression as an escape hatch |
| `with_("relation")` | chainable | explicit eager loading — see below |
| `get`, `first`, `find`, `count`, `exists` | terminal | execute against the current session |
| `paginate(per_page, page)` | terminal | returns a `Paginator` |

`.statement` on any `QueryBuilder` is a real SQLAlchemy `Select` — nothing
here is a second query language with its own execution model.

### Pagination

```python
paginator = User.query().paginate(per_page=20, page=1)
paginator.data           # the page's rows
paginator.current_page
paginator.total
paginator.last_page
paginator.to_dict()       # {"data": [...], "meta": {...}}
```

See [Validation & API Resources](validation-and-api.md) for turning a
`Paginator` directly into a JSON response via `Resource.paginated(...)`.

## Relationships

Thin, named wrappers around SQLAlchemy's `relationship()` — genuinely thin,
not a second relationship engine:

```python
from sqlalchemy import ForeignKey
from pyforge import has_many, belongs_to

class Author(Model):
    __tablename__ = "authors"
    books: Mapped[list["Book"]] = has_many("Book", back_populates="author")

class Book(Model):
    __tablename__ = "books"
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped[Author] = belongs_to("Author", back_populates="books")
```

`has_one`, `has_many`, `belongs_to`, and `belongs_to_many` are all available.

**Eager loading is always explicit** — never an implicit default, so query
cost stays predictable:

```python
Author.query().with_("books").first()   # applies selectinload
```

Touching `author.books` without `.with_(...)` just issues a normal lazy-load
query (safe here specifically because the ORM is synchronous — no async
lazy-loading hazard).

## UUID / ULID primary keys

Primary-key strategy is chosen by **base class**, not mixin composition
(SQLAlchemy declarative column overriding via mixin MRO is fragile enough
that this is the more robust design):

```python
from pyforge import UUIDModel, ULIDModel

class Order(UUIDModel):
    __tablename__ = "orders"

class Event(ULIDModel):   # sortable-by-creation-time
    __tablename__ = "events"
```

`Model` itself uses an auto-incrementing integer primary key by default.

## Soft deletes and timestamps

```python
from pyforge import SoftDeletesMixin, TimestampsMixin

class Post(TimestampsMixin, SoftDeletesMixin, Model):
    __tablename__ = "posts"
```

- `TimestampsMixin` — adds `created_at`/`updated_at`, kept in sync
  automatically via SQLAlchemy client-side `default`/`onupdate` callables.
  Application code never sets these.
- `SoftDeletesMixin` — adds a nullable `deleted_at`. `.query()`/`.where()`/
  `.all()` exclude soft-deleted rows by default; `instance.delete()` sets
  `deleted_at` instead of issuing a real `DELETE`. Pass
  `Model.query(with_trashed=True)` to include soft-deleted rows.

## What this deliberately doesn't do

- No custom query language that diverges from SQLAlchemy's own execution
  model — every `QueryBuilder` terminal method is explainable as "this ran
  the SQLAlchemy statement you'd have written by hand."
- No hidden N+1-query magic.
- No `--autogenerate`-by-default migration workflow (see
  [Migrations, Factories & Seeders](migrations-and-seeders.md)).
- Route-model binding (`id: int` auto-resolving to a `User`) isn't built —
  call `User.find_or_fail(id)` in the controller yourself.

## The escape hatch

`pyforge.database.current_session()` returns a real
`sqlalchemy.orm.Session`. Nothing prevents dropping to raw SQLAlchemy for a
query the builder doesn't express well:

```python
from pyforge.database import current_session
from sqlalchemy import text

rows = current_session().execute(text("SELECT ...")).all()
```
