from collections.abc import Iterator
from typing import Any, ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from pyforge.database import DatabaseManager, current_database, session_scope, set_current_database
from pyforge.orm import Base, Model
from pyforge.tenancy import (
    TenantDatabaseManager,
    TenantResolutionMiddleware,
    TenantScopedMixin,
    current_tenant_id,
    current_tenant_id_or_none,
    header_tenant_resolver,
    set_current_tenant,
    subdomain_tenant_resolver,
    tenant_scope,
)


class Post(TenantScopedMixin, Model):
    __tablename__ = "tenancy_test_posts"

    title: Mapped[str] = mapped_column(String(255))


# --- context ---


def test_current_tenant_id_raises_when_unset() -> None:
    set_current_tenant(None)
    with pytest.raises(RuntimeError):
        current_tenant_id()
    assert current_tenant_id_or_none() is None


def test_tenant_scope_sets_and_restores() -> None:
    set_current_tenant(None)
    with tenant_scope("acme"):
        assert current_tenant_id() == "acme"
        with tenant_scope("globex"):
            assert current_tenant_id() == "globex"
        assert current_tenant_id() == "acme"
    assert current_tenant_id_or_none() is None


# --- shared-database strategy ---


@pytest.fixture
def db(tmp_path) -> Iterator[DatabaseManager]:
    manager = DatabaseManager(
        {
            "default": "sqlite",
            "connections": {"sqlite": {"driver": "sqlite", "database": str(tmp_path / "tenancy.sqlite")}},
        }
    )
    Base.metadata.create_all(manager.engine())
    set_current_database(manager)
    try:
        yield manager
    finally:
        set_current_database(None)
        manager.dispose()


def test_create_stamps_current_tenant(db: DatabaseManager) -> None:
    with tenant_scope("acme"), session_scope():
        post = Post.create(title="Acme post")
        assert post.tenant_id == "acme"  # sqlite stores it untyped either way


def test_create_overrides_a_caller_supplied_tenant_id(db: DatabaseManager) -> None:
    """A controller doing something like Post.create(**request.validated())
    must not be able to leak a spoofed tenant_id from request data into a
    cross-tenant write — create() always wins over whatever was passed in."""
    with tenant_scope("acme"), session_scope():
        post = Post.create(title="Sneaky", tenant_id="globex")
        assert post.tenant_id == "acme"


def test_query_is_scoped_to_current_tenant(db: DatabaseManager) -> None:
    with session_scope():
        with tenant_scope("acme"):
            Post.create(title="Acme 1")
            Post.create(title="Acme 2")
        with tenant_scope("globex"):
            Post.create(title="Globex 1")

    with session_scope(), tenant_scope("acme"):
        titles = {p.title for p in Post.all()}
        assert titles == {"Acme 1", "Acme 2"}
        assert Post.query().count() == 2

    with session_scope(), tenant_scope("globex"):
        titles = {p.title for p in Post.all()}
        assert titles == {"Globex 1"}


def test_find_cannot_cross_tenant_boundary(db: DatabaseManager) -> None:
    with session_scope(), tenant_scope("acme"):
        post = Post.create(title="Acme secret")
        post_id = post.id

    with session_scope(), tenant_scope("globex"):
        assert Post.find(post_id) is None  # exists, but not for this tenant

    with session_scope(), tenant_scope("acme"):
        assert Post.find(post_id) is not None


def test_no_current_tenant_means_unscoped(db: DatabaseManager) -> None:
    with session_scope():
        with tenant_scope("acme"):
            Post.create(title="Acme post")
        with tenant_scope("globex"):
            Post.create(title="Globex post")

    with session_scope():
        set_current_tenant(None)
        assert len(Post.all()) == 2  # no tenant set -> no filter applied


# --- database-per-tenant strategy ---


def test_tenant_database_manager_routes_to_distinct_engines(tmp_path) -> None:
    def connection_for_tenant(tenant_id: Any) -> dict:
        return {"driver": "sqlite", "database": str(tmp_path / f"{tenant_id}.sqlite")}

    manager = TenantDatabaseManager(connection_for_tenant=connection_for_tenant)
    set_current_database(manager)
    try:
        with tenant_scope("acme"):
            Base.metadata.create_all(manager.engine())
            with session_scope():
                Post.create(title="Acme post")

        with tenant_scope("globex"):
            Base.metadata.create_all(manager.engine())
            with session_scope():
                assert Post.all() == []  # a completely separate database/file

        with tenant_scope("acme"), session_scope():
            assert len(Post.all()) == 1

        assert manager.engine("acme") is not manager.engine("globex")
        assert (tmp_path / "acme.sqlite").exists()
        assert (tmp_path / "globex.sqlite").exists()
    finally:
        set_current_database(None)
        manager.dispose()


def test_current_database_returns_tenant_manager(tmp_path) -> None:
    manager = TenantDatabaseManager(
        connection_for_tenant=lambda t: {"driver": "sqlite", "database": str(tmp_path / f"{t}.sqlite")}
    )
    set_current_database(manager)
    try:
        assert current_database() is manager
    finally:
        set_current_database(None)
        manager.dispose()


# --- middleware / resolvers ---


def test_subdomain_tenant_resolver() -> None:
    class FakeRequest:
        headers: ClassVar[dict[str, str]] = {"host": "acme.myapp.com"}

    assert subdomain_tenant_resolver(FakeRequest()) == "acme"  # type: ignore[arg-type]

    class FakeRequestNoSubdomain:
        headers: ClassVar[dict[str, str]] = {"host": "myapp.com"}

    assert subdomain_tenant_resolver(FakeRequestNoSubdomain()) is None  # type: ignore[arg-type]


def test_header_tenant_resolver() -> None:
    resolver = header_tenant_resolver("X-Tenant-ID")

    class FakeRequest:
        headers: ClassVar[dict[str, str]] = {"X-Tenant-ID": "acme"}

    assert resolver(FakeRequest()) == "acme"  # type: ignore[arg-type]


def test_tenant_resolution_middleware_sets_tenant_for_the_request(db: DatabaseManager) -> None:
    app = FastAPI()
    app.add_middleware(TenantResolutionMiddleware, resolver=header_tenant_resolver("X-Tenant-ID"))

    @app.get("/whoami")
    async def whoami() -> dict:
        return {"tenant": current_tenant_id_or_none()}

    with TestClient(app) as client:
        assert client.get("/whoami").json() == {"tenant": None}
        assert client.get("/whoami", headers={"X-Tenant-ID": "acme"}).json() == {"tenant": "acme"}
