# Database Architecture

**Status: implemented — Phase 2.** Everything below exists, is covered by
tests in `tests/test_database_manager.py`, `tests/test_orm.py`,
`tests/test_schema.py`, and `tests/test_factory_seeder.py`, and has been
verified against a real generated project (`pyforge new` → `make:model` →
`migrate:make` → `migrate` → CRUD through a real HTTP controller). See
[09-roadmap.md](09-roadmap.md#phase-2--database-implemented) for the
checklist.

## Ground rules

- SQLAlchemy 2.x is the engine. PyForge does not implement its own SQL
  dialect handling, connection pooling, or result mapping — it wraps
  SQLAlchemy the way `Router` wraps FastAPI's `APIRouter`: convenience on
  top, full escape hatch underneath.
- Alembic is the migration engine, for the same reason.
- MySQL is fully supported from the start (`pymysql` is a core dependency);
  PostgreSQL and SQLite work identically through the same SQLAlchemy dialect
  layer (Postgres needs `psycopg2`/`psycopg` installed separately — not
  bundled, since only MySQL support was required day one).
- The advanced escape hatch is always a real `sqlalchemy.orm.Session` —
  never a PyForge-specific session-lookalike. `QueryBuilder.statement` is
  always a real SQLAlchemy `Select`.

## Sync, not async — a deliberate choice

The rest of PyForge is async-first, but the ORM is built on **plain,
synchronous SQLAlchemy**, not `sqlalchemy.ext.asyncio`. Two reasons:

1. The spec's own examples (`User.find(1)`, `User.create(...)`) show no
   `await` anywhere — an async ORM wouldn't actually match the
   Active-Record-style ergonomics being asked for.
2. Async SQLAlchemy plus Alembic is a real source of friction in practice
   (lazy-loading a relationship inside `async def` code raises
   `MissingGreenlet` unless every access path is either eager-loaded or
   wrapped; migrations typically need a *second*, sync engine/driver anyway
   since Alembic's `op.*` runs synchronously). Sync SQLAlchemy sidesteps
   both problems entirely and is, in practice, the most common pattern in
   production FastAPI codebases today.

The trade-off: a `Model` call from an `async def` controller briefly blocks
the event loop for that request. For typical CRUD workloads this is a
non-issue (matching countless real FastAPI+SQLAlchemy-sync apps in
production); for a genuinely high-concurrency hot path, nothing stops a
developer from using a real `sqlalchemy.ext.asyncio.AsyncSession` directly
instead — that's the "advanced tier" escape hatch, always available,
never blocked by the framework.

## 1. Connection / session management (`pyforge.database`)

`config/database.py`'s `connections` dict feeds `DatabaseManager`, which
lazily builds and caches one SQLAlchemy `Engine` + `sessionmaker` per named
connection. `PyForge.__init__` builds one automatically whenever
`config/database.py` exists, and wraps every HTTP request in a
`session_scope()` via `DatabaseSessionMiddleware` — committed on a
successful response, rolled back if the handler raises — so `Model` methods
work in any controller with **zero explicit wiring**:

```python
class PostController:
    async def store(self, title: str) -> dict:
        post = Post.create(title=title)  # no Depends(), no session param
        return {"id": post.id, "title": post.title}
```

For code outside an HTTP request (scripts, seeders, tests), open one
manually: `with session_scope(): ...`. A FastAPI-dependency form
(`Depends(get_session)`) is also available for handlers that want the
session injected explicitly instead of relying on the automatic one.

## 2. `Model` base class (`pyforge.orm`)

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from pyforge import Model

class User(Model):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)

User.all()
User.find(1)
User.where("email", "=", "test@example.com").first()
User.where("active", True).get()
User.create(name="John", email="john@example.com")
```

`Model` is a thin Active-Record-style façade over a SQLAlchemy declarative
class (`pyforge.orm.Base`, a plain `DeclarativeBase`) — `find`/`where`/
`create`/`update`/`delete`/`save` are convenience methods over
`QueryBuilder` and the current session. Columns are declared with plain
SQLAlchemy 2.0 typed `Mapped[...]`/`mapped_column(...)` — not a new column
DSL (that's reserved for *migrations*; see below).

**Primary key strategy is chosen by base class, not by mixin composition:**
`Model` (auto-incrementing integer, the default), `UUIDModel`, and
`ULIDModel` (sortable-by-creation-time, generated in-house — see
`pyforge.orm.ulid`). SQLAlchemy declarative column overriding via mixin MRO
is fragile enough that picking a base class is the more robust design,
even though the original brief phrased this as "mixins."

`ModelNotFoundError` is raised by `find_or_fail`.

## 3. Query builder (`pyforge.orm.QueryBuilder`)

```python
User.query() \
    .where("active", True) \
    .order_by("created_at", "desc") \
    .paginate(per_page=20, page=1)
```

Every chained method (`where`, `or_where`, `where_in`, `where_null`,
`where_not_null`, `where_between`, `order_by`, `group_by`, `having`, `join`,
`left_join`, `select`, `limit`, `offset`, `with_`) mutates and returns
`self`, translating into the equivalent SQLAlchemy Core construct against
`.statement` (a real `Select`). Terminal methods (`get`, `first`, `find`,
`count`, `exists`, `paginate`) execute it against
`pyforge.database.current_session()`. `or_where` combines with the
*immediately preceding* condition (documented limitation — arbitrary
operator-precedence grouping across many conditions isn't supported).

`paginate(per_page, page)` returns a `Paginator` dataclass
(`.data`, `.current_page`, `.per_page`, `.total`, `.last_page`,
`.to_dict()`) matching the `{"data": [...], "meta": {...}}` envelope from
the original spec — turning that into an actual JSON response automatically
is a Phase 3 API-resource concern; for now a controller shapes it itself
(`return paginator.to_dict()`).

## 4. Relationships (`pyforge.orm.relationships`)

`has_one`, `has_many`, `belongs_to`, `belongs_to_many` are thin, named
wrappers around SQLAlchemy's `relationship()` — genuinely thin, not a second
relationship engine:

```python
class Author(Model):
    __tablename__ = "authors"
    books: Mapped[list["Book"]] = has_many("Book", back_populates="author")

class Book(Model):
    __tablename__ = "books"
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped[Author] = belongs_to("Author", back_populates="books")
```

Eager loading is always an explicit, opt-in call —
`Author.query().with_("books").first()` applies `selectinload` — never an
implicit default, so query cost stays predictable. Since the ORM is sync,
there's no async lazy-loading hazard either: touching `author.books` outside
`.with_(...)` just issues a normal lazy-load query.

## 5. Migrations (`pyforge.database.schema.Schema`, `pyforge.database.migrations`)

```bash
pyforge migrate:make create_users_table
pyforge migrate
pyforge migrate:rollback [--step N]
pyforge migrate:status
pyforge make:model User --migration   # generates the model AND the migration
```

```python
def upgrade() -> None:
    with Schema.create("users") as table:
        table.id()
        table.string("name")
        table.string("email").unique()
        table.boolean("active").default(True)
        table.timestamps()

def downgrade() -> None:
    Schema.drop("users")
```

This *is* Alembic — `pyforge migrate:make` calls `alembic.command.revision`
against a `Config` built programmatically (`build_alembic_config`, no
`alembic.ini` needed: the generated project's `database/migrations/env.py`
resolves the connection from `config/database.py` the same way the running
app does, so there's one source of truth for the URL, not two). `Schema`
(`Schema.create`, `Schema.table` for ALTER-style migrations, `Schema.drop`)
is a small, readable layer over real `alembic.op.*` calls — `table.string(...)`,
`.unique()`, `.nullable()`, `.default(...)`, `.references(...)`,
`.timestamps()`, `.soft_deletes()`, `.drop_column(...)` — nothing here
replaces Alembic's revision graph, versioning table, or (if you want it)
`--autogenerate`.

A generated migration's filename is smart-templated: `migrate:make
create_users_table` (matching `create_<table>_table`) pre-fills a working
`Schema.create(...)` skeleton; any other name gets a generic
`Schema.table(...)` skeleton to fill in. This lives in
`database/migrations/script.py.mako` in every generated project (a custom
Mako template with the table-name-guessing logic embedded directly in it),
not in the framework's Python code — so a project can customize its own
skeleton without patching PyForge.

**Migration-time `.default(value)` is a real database-level `server_default`**,
not SQLAlchemy's client-side-only `default=` — a raw `INSERT` from outside
the ORM (another tool, a seeder using a plain connection) has to see it too,
since migrations describe DDL, not ORM insert behavior. Common Python
literals (`bool`, `int`, `float`, `str`) are converted automatically; pass a
SQLAlchemy expression (`sa.func.now()`) for anything else. `.timestamps()`
columns are nullable with **no** database default — populating them is
`TimestampsMixin`'s job (see below), not the schema's; this exact split
(and why it matters) is covered by a regression test in `tests/test_schema.py`
after an earlier version of this got it backwards.

## 6. Cross-cutting concerns

- **Soft deletes** (`SoftDeletesMixin`): adds a nullable `deleted_at`.
  `Model.query()`/`where()`/`all()` exclude soft-deleted rows by default
  (unless built with `Model.query(with_trashed=True)`); `instance.delete()`
  sets `deleted_at` instead of issuing a `DELETE`.
- **Timestamps** (`TimestampsMixin`): adds `created_at`/`updated_at`, kept
  in sync via SQLAlchemy client-side `default`/`onupdate` callables,
  evaluated on flush — application code never sets these.
- **UUID / ULID primary keys**: `UUIDModel`/`ULIDModel` base classes (see
  above), not mixins.
- **Factories** (`pyforge.orm.Factory`): `UserFactory.create()`,
  `UserFactory.create_batch(10)`, and instance-level "trait" chaining
  (`UserFactory().admin().create()`) all work from one method body via a
  small custom descriptor (`_HybridMethod`) that builds a default instance
  when called on the class, or reuses the instance when called after
  `.state(...)`/a custom trait method.
- **Seeders** (`pyforge.orm.Seeder`): `pyforge db:seed` runs
  `database.seeders.database_seeder.DatabaseSeeder().run()` (or
  `--class <dotted.path>`) inside a `session_scope()`.
- **Transactions**: not a separate abstraction — `session_scope()` already
  commits on success and rolls back on any exception; for a narrower
  transaction, use the session's own `with session.begin_nested(): ...`.

## What this deliberately does not do

- No custom query language or ORM DSL that diverges from SQLAlchemy's own
  execution model — every `QueryBuilder` terminal method is explainable as
  "this ran the SQLAlchemy statement you'd have written by hand."
- No hidden N+1-query magic — eager loading is always an explicit
  `.with_(...)` call, never an implicit default.
- No MySQL-only helpers in the shared `Model`/`QueryBuilder` layer.
- No `--autogenerate`-by-default migration workflow — `migrate:make`
  produces an explicit, readable `Schema` skeleton instead, since a
  Phase-2-fresh ORM's autogenerate diffs are more likely to surprise than help.
