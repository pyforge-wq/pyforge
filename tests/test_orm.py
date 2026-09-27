from collections.abc import Iterator

import pytest
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from pyforge.database import DatabaseManager, session_scope, set_current_database
from pyforge.orm import (
    Base,
    Model,
    ModelNotFoundError,
    SoftDeletesMixin,
    TimestampsMixin,
    belongs_to,
    has_many,
)


class Author(Model):
    __tablename__ = "orm_test_authors"

    name: Mapped[str] = mapped_column(String(255))
    books: Mapped[list["Book"]] = has_many("Book", back_populates="author")


class Book(Model):
    __tablename__ = "orm_test_books"

    title: Mapped[str] = mapped_column(String(255))
    author_id: Mapped[int] = mapped_column(ForeignKey("orm_test_authors.id"))
    author: Mapped[Author] = belongs_to("Author", back_populates="books")


class Note(TimestampsMixin, SoftDeletesMixin, Model):
    __tablename__ = "orm_test_notes"

    body: Mapped[str] = mapped_column(String(255))


@pytest.fixture
def db(tmp_path) -> Iterator[DatabaseManager]:
    manager = DatabaseManager(
        {
            "default": "sqlite",
            "connections": {"sqlite": {"driver": "sqlite", "database": str(tmp_path / "orm.sqlite")}},
        }
    )
    Base.metadata.create_all(manager.engine())
    set_current_database(manager)
    try:
        yield manager
    finally:
        set_current_database(None)
        manager.dispose()


def test_create_and_find(db: DatabaseManager) -> None:
    with session_scope():
        author = Author.create(name="Ada Lovelace")
        author_id = author.id

    with session_scope():
        found = Author.find(author_id)
        assert found is not None
        assert found.name == "Ada Lovelace"


def test_find_returns_none_for_missing_row(db: DatabaseManager) -> None:
    with session_scope():
        assert Author.find(999) is None


def test_find_or_fail_raises(db: DatabaseManager) -> None:
    with session_scope(), pytest.raises(ModelNotFoundError):
        Author.find_or_fail(999)


def test_all_and_where(db: DatabaseManager) -> None:
    with session_scope():
        Author.create(name="Ada Lovelace")
        Author.create(name="Alan Turing")

    with session_scope():
        assert len(Author.all()) == 2
        assert Author.where("name", "Alan Turing").first().name == "Alan Turing"
        assert Author.where("name", "=", "Ada Lovelace").first().name == "Ada Lovelace"


def test_update_and_delete(db: DatabaseManager) -> None:
    with session_scope():
        author = Author.create(name="Ada Lovelace")
        author_id = author.id

    with session_scope():
        author = Author.find(author_id)
        author.update(name="Ada, Countess of Lovelace")

    with session_scope():
        assert Author.find(author_id).name == "Ada, Countess of Lovelace"
        Author.find(author_id).delete()

    with session_scope():
        assert Author.find(author_id) is None


def test_relationship_has_many_and_belongs_to(db: DatabaseManager) -> None:
    with session_scope():
        author = Author.create(name="Ada Lovelace")
        Book.create(title="Notes on the Analytical Engine", author_id=author.id)
        Book.create(title="Sketch of the Analytical Engine", author_id=author.id)

    with session_scope():
        author = Author.query().with_("books").where("name", "Ada Lovelace").first()
        assert {b.title for b in author.books} == {
            "Notes on the Analytical Engine",
            "Sketch of the Analytical Engine",
        }
        book = Book.where("title", "Notes on the Analytical Engine").first()
        assert book.author.name == "Ada Lovelace"


def test_timestamps_mixin_sets_created_and_updated_at(db: DatabaseManager) -> None:
    with session_scope():
        note = Note.create(body="hello")
        assert note.created_at is not None
        assert note.updated_at is not None
        first_updated_at = note.updated_at

    with session_scope():
        note = Note.find(note.id)
        note.update(body="hello, world")
        assert note.updated_at >= first_updated_at


def test_soft_deletes_mixin_hides_deleted_rows_and_delete_is_an_update(db: DatabaseManager) -> None:
    with session_scope():
        note = Note.create(body="secret")
        note_id = note.id

    with session_scope():
        Note.find(note_id).delete()

    with session_scope():
        assert Note.find(note_id) is None
        assert Note.all() == []
        trashed = Note.query(with_trashed=True).find(note_id)
        assert trashed is not None
        assert trashed.deleted_at is not None


def test_query_builder_chaining(db: DatabaseManager) -> None:
    with session_scope():
        Author.create(name="Ada Lovelace")
        Author.create(name="Alan Turing")
        Author.create(name="Grace Hopper")

    with session_scope():
        names = [
            a.name
            for a in Author.query().where("name", "!=", "Alan Turing").order_by("name", "desc").get()
        ]
        assert names == ["Grace Hopper", "Ada Lovelace"]
        assert Author.query().count() == 3
        assert Author.where("name", "Ada Lovelace").exists() is True
        assert Author.where("name", "Nobody").exists() is False


def test_or_where(db: DatabaseManager) -> None:
    with session_scope():
        Author.create(name="Ada Lovelace")
        Author.create(name="Alan Turing")
        Author.create(name="Grace Hopper")

    with session_scope():
        names = {
            a.name
            for a in Author.query().where("name", "Ada Lovelace").or_where("name", "Alan Turing").get()
        }
        assert names == {"Ada Lovelace", "Alan Turing"}


def test_paginate(db: DatabaseManager) -> None:
    with session_scope():
        for i in range(25):
            Author.create(name=f"Author {i}")

    with session_scope():
        page = Author.query().order_by("id").paginate(per_page=10, page=2)
        assert len(page.data) == 10
        assert page.current_page == 2
        assert page.per_page == 10
        assert page.total == 25
        assert page.last_page == 3
        assert page.data[0].name == "Author 10"
