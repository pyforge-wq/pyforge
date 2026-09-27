# Migrations, Factories & Seeders

## Migrations

Migrations are real Alembic revisions — `pyforge migrate:make` calls
`alembic.command.revision` against a `Config` built programmatically, so
there's no `alembic.ini` to manage separately. The generated project's
`database/migrations/env.py` resolves the connection from
`config/database.py`, the same way the running app does — one source of
truth for the URL, not two.

```bash
pyforge migrate:make create_posts_table
pyforge migrate
pyforge migrate:rollback [--step N]
pyforge migrate:status
```

A migration matching `create_<table>_table` is pre-filled with a working
skeleton:

```python
from pyforge.database import Schema

def upgrade() -> None:
    with Schema.create("posts") as table:
        table.id()
        table.string("title")
        table.string("slug").unique()
        table.boolean("published").default(False)
        table.timestamps()

def downgrade() -> None:
    Schema.drop("posts")
```

Any other migration name gets a generic ALTER-style skeleton via
`Schema.table(...)`:

```python
def upgrade() -> None:
    with Schema.table("posts") as table:
        table.string("subtitle").nullable()

def downgrade() -> None:
    with Schema.table("posts") as table:
        table.drop_column("subtitle")
```

### Schema builder reference

`table.string(...)`, `.unique()`, `.nullable()`, `.default(...)`,
`.references(...)`, `.timestamps()`, `.soft_deletes()`, `.drop_column(...)`
— a small, readable layer directly over real `alembic.op.*` calls. Nothing
here replaces Alembic's revision graph, versioning table, or
`--autogenerate` if you want it.

!!! warning "`.default(value)` is a real database-level default"
    Migration-time `.default(value)` becomes a `server_default` — visible to
    a raw `INSERT` from outside the ORM, not just SQLAlchemy's client-side
    `default=`. Common Python literals (`bool`, `int`, `float`, `str`) are
    converted automatically; pass a SQLAlchemy expression
    (`sa.func.now()`) for anything else. `.timestamps()` columns are
    deliberately nullable with **no** database default — populating them is
    `TimestampsMixin`'s job at the ORM layer, not the schema's.

### `--autogenerate` isn't the default

`pyforge migrate:make` produces an explicit, readable `Schema` skeleton
instead of diffing your models automatically. This is deliberate — a young
ORM's autogenerate diffs are more likely to surprise than help. Nothing
stops you from using Alembic's own `--autogenerate` flag directly if you
want it; PyForge just doesn't wire it up as the default path.

## Generate a model and its migration together

```bash
pyforge make:model Post --migration
```

Table names are naively pluralized (`User` → `users`) — rename
`__tablename__` yourself for irregular plurals.

## Factories

```python
from uuid import uuid4
from pyforge import Factory
from app.models.user import User

class UserFactory(Factory):
    model = User

    def definition(self) -> dict:
        return {"name": "Test User", "email": f"user{uuid4()}@example.com"}

    def admin(self) -> "UserFactory":
        return self.state(role="admin")
```

```python
UserFactory.create()                    # persisted
UserFactory.create(name="Override")     # persisted, with an attribute override
UserFactory.create_batch(10)            # 10 persisted rows
UserFactory.make()                      # built, not persisted
UserFactory().admin().create()          # a named trait, one-off override
UserFactory().state(name="Ada").create()
```

Class-level and instance-level calls both work from one method body — a
small custom descriptor builds a default instance when called on the class,
or reuses the instance after `.state(...)`/a trait method.

## Seeders

```python
# database/seeders/database_seeder.py
from pyforge import Seeder
from app.models.user import User

class DatabaseSeeder(Seeder):
    def run(self) -> None:
        User.create(name="Admin", email="admin@example.com")
```

```bash
pyforge db:seed                          # runs DatabaseSeeder inside a session_scope()
pyforge db:seed --class app.seeders.PostSeeder
```

## Transactions

Not a separate abstraction — `session_scope()` already commits on success
and rolls back on any exception. For a narrower transaction within one
request or script, use the session's own nested-transaction API:

```python
from pyforge.database import current_session

with current_session().begin_nested():
    ...
```
