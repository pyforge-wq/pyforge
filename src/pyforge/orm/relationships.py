from __future__ import annotations

from typing import Any

from sqlalchemy.orm import relationship


def has_one(target: str, **kwargs: Any) -> Any:
    """A one-to-one relationship: the *other* table holds the foreign key.
    ``Author.profile = has_one("Profile")``."""
    return relationship(target, uselist=False, **kwargs)


def has_many(target: str, **kwargs: Any) -> Any:
    """A one-to-many relationship: the *other* table holds the foreign key.
    ``Author.posts = has_many("Post")``."""
    return relationship(target, uselist=True, **kwargs)


def belongs_to(target: str, **kwargs: Any) -> Any:
    """The inverse of ``has_one``/``has_many``: *this* table holds the
    foreign key. ``Post.author = belongs_to("Author")``."""
    return relationship(target, uselist=False, **kwargs)


def belongs_to_many(target: str, *, secondary: Any, **kwargs: Any) -> Any:
    """A many-to-many relationship through an explicit association table —
    ``secondary`` is a real SQLAlchemy ``Table``, declared the normal
    SQLAlchemy way. ``Post.tags = belongs_to_many("Tag", secondary=post_tags)``."""
    return relationship(target, secondary=secondary, uselist=True, **kwargs)
