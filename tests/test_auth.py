from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from pyforge.auth import (
    ApiTokenAuth,
    Auth,
    Policy,
    authorize,
    current_user,
    hash_password,
    permission,
    role,
    set_default_auth,
)
from pyforge.database import DatabaseManager, session_scope, set_current_database
from pyforge.orm import Base, Model


class User(Model):
    __tablename__ = "auth_test_users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")

    def has_permission(self, name: str) -> bool:
        return self.role == "admin"


class PersonalAccessToken(Model):
    __tablename__ = "auth_test_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("auth_test_users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)


class Post(Model):
    __tablename__ = "auth_test_posts"

    author_id: Mapped[int] = mapped_column(ForeignKey("auth_test_users.id"))
    title: Mapped[str] = mapped_column(String(255))


class PostPolicy(Policy):
    def update(self, user: Any, post: Post) -> bool:
        return user.id == post.author_id


# A module-level Auth instance, so the decorator-based tests below can
# define their controllers at module scope too — Router only recognizes a
# handler as a controller action when its __qualname__ isn't nested inside
# a function (e.g. a test body); see test_router.py's docstring for the
# same constraint.
auth = Auth(User, secret="test-secret", access_ttl_minutes=60, refresh_ttl_minutes=60)

# Realistically this happens in a service provider's register(), which runs
# before an app's routes/ (and therefore its controllers) get imported — see
# docs/architecture/03-public-api-design.md's auth section. Mirroring that
# ordering here (set before the decorated classes below are defined) is what
# makes @role("admin") with no explicit get_user= valid at class-body time.
set_default_auth(auth)


class AdminController:
    @role("admin", get_user=auth.required)
    async def stats(self) -> dict:
        return {"secret": True}


class RegisterController:
    @permission("users.create", get_user=auth.required)
    async def store(self) -> dict:
        return {"created": True}


class DefaultAuthAdminController:
    @role("admin")
    async def stats(self) -> dict:
        return {"secret": True}


@pytest.fixture
def db(tmp_path) -> Iterator[DatabaseManager]:
    manager = DatabaseManager(
        {
            "default": "sqlite",
            "connections": {"sqlite": {"driver": "sqlite", "database": str(tmp_path / "auth.sqlite")}},
        }
    )
    Base.metadata.create_all(manager.engine())
    set_current_database(manager)
    try:
        yield manager
    finally:
        set_current_database(None)
        manager.dispose()




def test_hash_password_roundtrip() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert Auth.verify_password("secret123", hashed) is True
    assert Auth.verify_password("wrong", hashed) is False


def test_attempt_succeeds_with_correct_credentials(db: DatabaseManager) -> None:
    with session_scope():
        User.create(email="ada@example.com", password_hash=hash_password("secret123"))

    with session_scope():
        user = auth.attempt("ada@example.com", "secret123")
        assert user is not None
        assert user.email == "ada@example.com"


def test_attempt_fails_with_wrong_password_or_unknown_email(db: DatabaseManager) -> None:
    with session_scope():
        User.create(email="ada@example.com", password_hash=hash_password("secret123"))

    with session_scope():
        assert auth.attempt("ada@example.com", "wrong") is None
        assert auth.attempt("nobody@example.com", "secret123") is None


def test_login_issues_working_access_and_refresh_tokens(db: DatabaseManager) -> None:
    with session_scope():
        user = User.create(email="ada@example.com", password_hash=hash_password("secret123"))
        tokens = auth.login(user)

    assert set(tokens) == {"access_token", "refresh_token", "token_type"}

    with session_scope():
        resolved = auth._user_for(tokens["access_token"], purpose="access")
        assert resolved is not None
        assert resolved.email == "ada@example.com"
        # a refresh token must not work as an access token
        assert auth._user_for(tokens["refresh_token"], purpose="access") is None


def test_refresh_exchanges_refresh_token_for_new_access_token(db: DatabaseManager) -> None:
    with session_scope():
        user = User.create(email="ada@example.com", password_hash=hash_password("secret123"))
        tokens = auth.login(user)

    with session_scope():
        new_tokens = auth.refresh(tokens["refresh_token"])
        assert "access_token" in new_tokens
        assert auth._user_for(new_tokens["access_token"], purpose="access").email == "ada@example.com"


def test_signed_tokens_are_purpose_scoped(db: DatabaseManager) -> None:
    with session_scope():
        user = User.create(email="ada@example.com", password_hash=hash_password("secret123"))
        token = auth.make_signed_token(user.id, purpose="password_reset", ttl_minutes=30)

    with session_scope():
        assert auth.verify_signed_token(token, purpose="password_reset") is not None
        assert auth.verify_signed_token(token, purpose="email_verification") is None


def test_required_dependency_protects_a_real_http_route(db: DatabaseManager) -> None:
    app = FastAPI()

    @app.get("/me")
    async def me(user: Any = Depends(auth.required)) -> dict:
        return {"id": user.id, "email": user.email}

    with session_scope():
        user = User.create(email="ada@example.com", password_hash=hash_password("secret123"))
        tokens = auth.login(user)

    with TestClient(app) as client, session_scope():
        assert client.get("/me").status_code == 401
        response = client.get("/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert response.status_code == 200
        assert response.json()["email"] == "ada@example.com"


def test_session_login_sets_a_working_cookie(db: DatabaseManager) -> None:
    from fastapi import Response

    app = FastAPI()

    @app.post("/login")
    async def login_route(response: Response) -> dict:
        user = User.where("email", "ada@example.com").first()
        auth.session_login(response, user, secure=False)  # TestClient's transport is plain http
        return {"ok": True}

    @app.get("/me")
    async def me(user: Any = Depends(auth.session_required)) -> dict:
        return {"id": user.id}

    with session_scope():
        User.create(email="ada@example.com", password_hash=hash_password("secret123"))

    with TestClient(app) as client, session_scope():
        assert client.get("/me").status_code == 401
        client.post("/login")
        response = client.get("/me")
        assert response.status_code == 200


def test_session_login_defaults_to_secure_and_is_not_sent_over_plain_http(db: DatabaseManager) -> None:
    """secure=True is the default — a real browser (and httpx's TestClient,
    which enforces the same cookie rules) won't send a secure cookie back
    over a plain http:// connection, so the session must not carry over."""
    from fastapi import Response

    app = FastAPI()

    @app.post("/login")
    async def login_route(response: Response) -> dict:
        user = User.where("email", "ada@example.com").first()
        auth.session_login(response, user)  # secure=True (default)
        return {"ok": True}

    @app.get("/me")
    async def me(user: Any = Depends(auth.session_required)) -> dict:
        return {"id": user.id}

    with session_scope():
        User.create(email="ada@example.com", password_hash=hash_password("secret123"))

    with TestClient(app) as client, session_scope():
        client.post("/login")
        response = client.get("/me")
        assert response.status_code == 401


def test_role_decorator_enforces_role(db: DatabaseManager) -> None:
    from pyforge.container import Container
    from pyforge.routing import Router

    app = FastAPI()
    router = Router(container=Container())
    router.get("/admin/stats", AdminController.stats)
    app.include_router(router.to_fastapi_router())

    with session_scope():
        admin = User.create(email="admin@example.com", password_hash=hash_password("x"), role="admin")
        user = User.create(email="user@example.com", password_hash=hash_password("x"), role="user")
        admin_tokens = auth.login(admin)
        user_tokens = auth.login(user)

    with TestClient(app) as client, session_scope():
        response = client.get("/admin/stats", headers={"Authorization": f"Bearer {admin_tokens['access_token']}"})
        assert response.status_code == 200

        response = client.get("/admin/stats", headers={"Authorization": f"Bearer {user_tokens['access_token']}"})
        assert response.status_code == 403


def test_permission_decorator_uses_has_permission(db: DatabaseManager) -> None:
    from pyforge.container import Container
    from pyforge.routing import Router

    app = FastAPI()
    router = Router(container=Container())
    router.post("/users", RegisterController.store)
    app.include_router(router.to_fastapi_router())

    with session_scope():
        admin = User.create(email="admin2@example.com", password_hash=hash_password("x"), role="admin")
        user = User.create(email="user2@example.com", password_hash=hash_password("x"), role="user")
        admin_tokens = auth.login(admin)
        user_tokens = auth.login(user)

    with TestClient(app) as client, session_scope():
        assert client.post(
            "/users", headers={"Authorization": f"Bearer {admin_tokens['access_token']}"}
        ).status_code == 200
        assert client.post(
            "/users", headers={"Authorization": f"Bearer {user_tokens['access_token']}"}
        ).status_code == 403


def test_default_auth_is_used_when_role_decorator_has_no_explicit_get_user(db: DatabaseManager) -> None:
    # set_default_auth(auth) already ran at module import time (see above),
    # which is what let DefaultAuthAdminController's bare @role("admin") work.
    from pyforge.container import Container
    from pyforge.routing import Router

    app = FastAPI()
    router = Router(container=Container())
    router.get("/admin/stats", DefaultAuthAdminController.stats)
    app.include_router(router.to_fastapi_router())

    with session_scope():
        admin = User.create(email="admin3@example.com", password_hash=hash_password("x"), role="admin")
        tokens = auth.login(admin)

    with TestClient(app) as client, session_scope():
        response = client.get(
            "/admin/stats", headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        assert response.status_code == 200


def test_policy_authorize(db: DatabaseManager) -> None:
    with session_scope():
        owner = User.create(email="owner@example.com", password_hash="x")
        other = User.create(email="other@example.com", password_hash="x")
        post = Post.create(author_id=owner.id, title="Hello")

        authorize(PostPolicy(), "update", owner, post)  # does not raise

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as excinfo:
            authorize(PostPolicy(), "update", other, post)
        assert excinfo.value.status_code == 403


def test_api_token_auth_end_to_end(db: DatabaseManager) -> None:
    api_tokens = ApiTokenAuth(PersonalAccessToken, User)

    app = FastAPI()

    @app.get("/me")
    async def me(user: Any = Depends(api_tokens.required)) -> dict:
        return {"id": user.id}

    with session_scope():
        user = User.create(email="ada4@example.com", password_hash="x")
        plaintext = api_tokens.issue(user)

    with TestClient(app) as client, session_scope():
        assert client.get("/me").status_code == 401
        assert client.get("/me", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401
        response = client.get("/me", headers={"Authorization": f"Bearer {plaintext}"})
        assert response.status_code == 200
        assert response.json()["id"] == user.id


def test_current_user_resolves_the_default_auth_lazily(db: DatabaseManager) -> None:
    # set_default_auth(auth) already ran at module import time; current_user
    # doesn't need a specific Auth instance in hand at all, unlike
    # Depends(auth.required) — it looks up default_auth() at request time.
    app = FastAPI()

    @app.get("/me")
    async def me(user: Any = Depends(current_user)) -> dict:
        return {"id": user.id}

    with session_scope():
        user = User.create(email="lazy@example.com", password_hash=hash_password("x"))
        tokens = auth.login(user)

    with TestClient(app) as client, session_scope():
        assert client.get("/me").status_code == 401
        response = client.get("/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert response.status_code == 200
        assert response.json()["id"] == user.id
