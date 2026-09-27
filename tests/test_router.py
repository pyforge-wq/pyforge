from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from pyforge.container import Container
from pyforge.middleware import middleware_registry
from pyforge.routing import Router


async def ping() -> dict:
    return {"pong": True}


class Greeter:
    async def hello(self, name: str) -> dict:
        return {"message": f"Hello, {name}!"}


class Counter:
    """A fresh instance is made by the container per request; this proves it."""

    def __init__(self) -> None:
        self.count = 0

    async def bump(self) -> dict:
        self.count += 1
        return {"count": self.count}


def build_app(router: Router) -> FastAPI:
    app = FastAPI()
    app.include_router(router.to_fastapi_router())
    return app


def test_plain_function_route_is_untouched() -> None:
    router = Router(container=Container())
    router.get("/ping", ping)

    client = TestClient(build_app(router))
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"pong": True}


def test_controller_action_is_wrapped_and_receives_path_params() -> None:
    router = Router(container=Container())
    router.get("/hello/{name}", Greeter.hello)

    client = TestClient(build_app(router))
    response = client.get("/hello/Ada")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Ada!"}


def test_controller_is_resolved_fresh_per_request() -> None:
    router = Router(container=Container())
    router.post("/bump", Counter.bump)

    client = TestClient(build_app(router))
    first = client.post("/bump").json()
    second = client.post("/bump").json()

    assert first == {"count": 1}
    assert second == {"count": 1}  # fresh Counter each time, not a shared singleton


def test_named_routes_are_recorded_and_reversible() -> None:
    router = Router(container=Container())
    router.get("/hello/{name}", Greeter.hello, name="greeter.hello")

    assert router.url("greeter.hello", name="Ada") == "/hello/Ada"


def test_group_applies_prefix_and_name_namespace() -> None:
    router = Router(container=Container())
    with router.group(prefix="/api/v1", name="v1") as group:
        group.get("/ping", ping, name="ping")

    client = TestClient(build_app(router))
    response = client.get("/api/v1/ping")

    assert response.status_code == 200
    assert router.url("v1.ping") == "/api/v1/ping"


def test_group_middleware_can_reject_requests() -> None:
    async def require_token(x_token: str | None = Header(default=None)) -> None:
        if x_token != "secret":
            raise HTTPException(status_code=401, detail="unauthorized")

    middleware_registry.register("auth-test", require_token)
    try:
        router = Router(container=Container())
        with router.group(prefix="/admin", middleware=["auth-test"]) as group:
            group.get("/ping", ping)
    finally:
        middleware_registry._middleware.pop("auth-test", None)

    client = TestClient(build_app(router))

    assert client.get("/admin/ping").status_code == 401
    assert client.get("/admin/ping", headers={"x-token": "secret"}).status_code == 200
