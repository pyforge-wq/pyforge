from collections.abc import Iterator

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from pyforge.database import DatabaseManager, session_scope, set_current_database
from pyforge.orm import Base, Factory, Model, Seeder


class Widget(Model):
    __tablename__ = "factory_test_widgets"

    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")


class WidgetFactory(Factory):
    model = Widget

    def definition(self) -> dict:
        return {"name": "Test Widget", "role": "user"}

    def admin(self) -> "WidgetFactory":
        return self.state(role="admin")


@pytest.fixture
def db(tmp_path) -> Iterator[DatabaseManager]:
    manager = DatabaseManager(
        {
            "default": "sqlite",
            "connections": {"sqlite": {"driver": "sqlite", "database": str(tmp_path / "factory.sqlite")}},
        }
    )
    Base.metadata.create_all(manager.engine())
    set_current_database(manager)
    try:
        yield manager
    finally:
        set_current_database(None)
        manager.dispose()


def test_class_level_create(db: DatabaseManager) -> None:
    with session_scope():
        widget = WidgetFactory.create()
        assert widget.name == "Test Widget"
        assert widget.id is not None


def test_class_level_create_with_overrides(db: DatabaseManager) -> None:
    with session_scope():
        widget = WidgetFactory.create(name="Custom")
        assert widget.name == "Custom"


def test_create_batch(db: DatabaseManager) -> None:
    with session_scope():
        widgets = WidgetFactory.create_batch(5)
        assert len(widgets) == 5
        assert len({w.id for w in widgets}) == 5


def test_state_chaining_is_preserved_through_instance_create(db: DatabaseManager) -> None:
    with session_scope():
        widget = WidgetFactory().admin().create()
        assert widget.role == "admin"
        assert widget.name == "Test Widget"


def test_state_chaining_with_inline_override(db: DatabaseManager) -> None:
    with session_scope():
        widget = WidgetFactory().admin().create(name="Root")
        assert widget.role == "admin"
        assert widget.name == "Root"


def test_make_does_not_persist(db: DatabaseManager) -> None:
    with session_scope():
        widget = WidgetFactory.make()
        assert widget.id is None
        assert Widget.all() == []


def test_seeder_runs_inside_session_scope(db: DatabaseManager) -> None:
    class WidgetSeeder(Seeder):
        def run(self) -> None:
            WidgetFactory.create_batch(3)

    with session_scope():
        WidgetSeeder().run()

    with session_scope():
        assert len(Widget.all()) == 3
