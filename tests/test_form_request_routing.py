from typing import ClassVar

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyforge.container import Container
from pyforge.routing import Router
from pyforge.validation import FormRequest


class CreateUserRequest(FormRequest):
    rules: ClassVar[dict[str, str]] = {
        "name": "required|string|max:255",
        "email": "required|email",
        "password": "required|min:8",
    }


class UserController:
    async def store(self, request: CreateUserRequest) -> dict:
        return {"validated": request.validated(), "name": request.name}


async def store_plain(request: CreateUserRequest) -> dict:
    return {"validated": request.validated()}


def build_app(router: Router) -> FastAPI:
    app = FastAPI()
    app.include_router(router.to_fastapi_router())
    return app


def test_form_request_is_injected_for_a_controller_action() -> None:
    router = Router(container=Container())
    router.post("/users", UserController.store)

    client = TestClient(build_app(router))
    response = client.post(
        "/users", json={"name": "Ada", "email": "ada@example.com", "password": "secretpw"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Ada"


def test_form_request_validation_failure_returns_422() -> None:
    router = Router(container=Container())
    router.post("/users", UserController.store)

    client = TestClient(build_app(router))
    response = client.post(
        "/users", json={"name": "Ada", "email": "not-an-email", "password": "short"}
    )

    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert "email" in errors
    assert "password" in errors


def test_form_request_is_injected_for_a_plain_function_route() -> None:
    router = Router(container=Container())
    router.post("/users", store_plain)

    client = TestClient(build_app(router))
    response = client.post(
        "/users", json={"name": "Ada", "email": "ada@example.com", "password": "secretpw"}
    )

    assert response.status_code == 200
    assert response.json()["validated"]["name"] == "Ada"


def test_plain_route_without_form_request_is_unaffected() -> None:
    router = Router(container=Container())

    async def ping() -> dict:
        return {"pong": True}

    router.get("/ping", ping)
    client = TestClient(build_app(router))
    assert client.get("/ping").json() == {"pong": True}
