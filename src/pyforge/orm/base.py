from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """The single declarative base every ``Model`` (and therefore every
    application model) shares, so Alembic's autogenerate and
    ``Base.metadata.create_all(...)`` (handy in tests) see every table."""
