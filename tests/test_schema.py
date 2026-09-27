from contextlib import contextmanager

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from pyforge.database.schema import Schema


@contextmanager
def operations_on(engine: sa.Engine):
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        with Operations.context(context):
            yield conn
        conn.commit()


def test_schema_create_builds_a_real_table(tmp_path) -> None:
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'schema.sqlite'}")

    with operations_on(engine), Schema.create("widgets") as table:
        table.id()
        table.string("name")
        table.string("email").unique()
        table.boolean("active").default(True)
        table.timestamps()

    columns = {c["name"] for c in sa.inspect(engine).get_columns("widgets")}
    assert columns == {"id", "name", "email", "active", "created_at", "updated_at"}


def test_default_and_timestamps_are_real_enough_for_a_bare_insert(tmp_path) -> None:
    """Regression test: `.default(...)` must produce a real database-level
    default (server_default), not a client-side-only SQLAlchemy default that
    silently does nothing for a plain INSERT — and `.timestamps()` columns
    must be nullable, since populating them is the ORM mixin's job, not the
    schema's. A raw `INSERT ... DEFAULT VALUES` with no ORM involved at all
    must succeed against a table built this way."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'defaults.sqlite'}")

    with operations_on(engine), Schema.create("gadgets") as table:
        table.id()
        table.boolean("active").default(True).nullable(False)
        table.integer("priority").default(3).nullable(False)
        table.string("status").default("pending").nullable(False)
        table.timestamps()

    with engine.connect() as conn:
        conn.execute(sa.text("INSERT INTO gadgets DEFAULT VALUES"))
        conn.commit()
        row = conn.execute(sa.text("SELECT active, priority, status, created_at FROM gadgets")).one()
        assert row.active == 1
        assert row.priority == 3
        assert row.status == "pending"
        assert row.created_at is None


def test_schema_create_supports_foreign_keys(tmp_path) -> None:
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'fk.sqlite'}")

    with operations_on(engine), Schema.create("authors") as table:
        table.id()
        table.string("name")

    with operations_on(engine), Schema.create("books") as table:
        table.id()
        table.string("title")
        table.foreign_id("author_id").references("authors")

    foreign_keys = sa.inspect(engine).get_foreign_keys("books")
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["referred_table"] == "authors"


def test_schema_table_adds_and_drops_columns(tmp_path) -> None:
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'alter.sqlite'}")

    with operations_on(engine), Schema.create("posts") as table:
        table.id()
        table.string("title")

    with operations_on(engine), Schema.table("posts") as table:
        table.text("body").nullable()

    columns = {c["name"] for c in sa.inspect(engine).get_columns("posts")}
    assert "body" in columns


def test_schema_drop_removes_the_table(tmp_path) -> None:
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'drop.sqlite'}")

    with operations_on(engine), Schema.create("temp") as table:
        table.id()

    with operations_on(engine):
        Schema.drop("temp")

    assert "temp" not in sa.inspect(engine).get_table_names()
