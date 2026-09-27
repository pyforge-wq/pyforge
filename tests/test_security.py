from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyforge.cache import Cache, MemoryCacheDriver
from pyforge.container import Container
from pyforge.routing import Router
from pyforge.security import SecurityHeadersMiddleware, rate_limit
from pyforge.security.rate_limit import _parse_rate


def test_parse_rate() -> None:
    assert _parse_rate("60/minute") == (60, 60)
    assert _parse_rate("5/second") == (5, 1)
    assert _parse_rate("1000/hour") == (1000, 3600)
    assert _parse_rate("10/day") == (10, 86400)


def test_parse_rate_rejects_unknown_period() -> None:
    with pytest.raises(ValueError):
        _parse_rate("10/fortnight")


class ThrottledController:
    @rate_limit("3/minute", cache=Cache(MemoryCacheDriver()))
    async def ping(self) -> dict:
        return {"pong": True}


_per_client_cache = Cache(MemoryCacheDriver())


class PerClientThrottledController:
    @rate_limit("1/minute", cache=_per_client_cache, key_func=lambda request: request.headers.get("X-Client", "default"))
    async def ping(self) -> dict:
        return {"pong": True}


def test_rate_limit_allows_up_to_the_limit_then_429s() -> None:
    router = Router(container=Container())
    router.get("/ping", ThrottledController.ping)
    app = FastAPI()
    app.include_router(router.to_fastapi_router())

    with TestClient(app) as client:
        for _ in range(3):
            assert client.get("/ping").status_code == 200
        response = client.get("/ping")
        assert response.status_code == 429


def test_rate_limit_tracks_separate_clients_independently() -> None:
    router = Router(container=Container())
    router.get("/ping", PerClientThrottledController.ping)
    app = FastAPI()
    app.include_router(router.to_fastapi_router())

    with TestClient(app) as client:
        assert client.get("/ping", headers={"X-Client": "a"}).status_code == 200
        assert client.get("/ping", headers={"X-Client": "a"}).status_code == 429
        assert client.get("/ping", headers={"X-Client": "b"}).status_code == 200


def test_security_headers_middleware_sets_expected_headers() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/")
    async def home() -> dict:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers
        assert "Strict-Transport-Security" not in response.headers  # plain http in tests


def test_security_headers_middleware_never_overrides_existing_header() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/")
    async def home() -> Any:
        from starlette.responses import JSONResponse

        return JSONResponse({"ok": True}, headers={"X-Frame-Options": "SAMEORIGIN"})

    with TestClient(app) as client:
        response = client.get("/")
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"


def test_security_headers_middleware_accepts_custom_csp() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, content_security_policy="default-src 'self'")

    @app.get("/")
    async def home() -> dict:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/")
        assert response.headers["Content-Security-Policy"] == "default-src 'self'"
