from pathlib import Path
from typing import ClassVar

from fastapi.testclient import TestClient

from pyforge import PyForge, Router, ServiceProvider
from pyforge.container import Container


class RecordingProvider(ServiceProvider):
    registered: ClassVar[list[str]] = []
    booted: ClassVar[list[str]] = []

    def register(self) -> None:
        RecordingProvider.registered.append("registered")

    def boot(self) -> None:
        RecordingProvider.booted.append("booted")


def make_project(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "app.py").write_text('config = {"name": "Test App"}\n')
    (tmp_path / ".env").write_text("APP_ENV=testing\n")
    return tmp_path


def test_loads_config_from_base_path(tmp_path: Path) -> None:
    make_project(tmp_path)
    app = PyForge(base_path=tmp_path, container=Container())

    assert app.config.get("app.name") == "Test App"


def test_env_file_is_loaded_into_process_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV_TEST_MARKER", raising=False)
    project = make_project(tmp_path)
    (project / ".env").write_text("APP_ENV_TEST_MARKER=from-dotenv\n")

    PyForge(base_path=tmp_path, container=Container())

    import os

    assert os.environ["APP_ENV_TEST_MARKER"] == "from-dotenv"


def test_register_routes_mounts_router_on_fastapi(tmp_path: Path) -> None:
    make_project(tmp_path)
    app = PyForge(base_path=tmp_path, container=Container())

    router = Router(container=app.container)
    router.get("/ping", lambda: {"pong": True})
    app.register_routes(router)

    with TestClient(app.fastapi) as client:
        response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"pong": True}


def test_asgi_call_delegates_to_fastapi(tmp_path: Path) -> None:
    make_project(tmp_path)
    app = PyForge(base_path=tmp_path, container=Container())

    with TestClient(app) as client:  # PyForge itself is ASGI-callable
        response = client.get("/docs")

    assert response.status_code == 200


def test_providers_register_immediately_and_boot_on_startup(tmp_path: Path) -> None:
    make_project(tmp_path)
    RecordingProvider.registered.clear()
    RecordingProvider.booted.clear()

    app = PyForge(base_path=tmp_path, container=Container())
    app.register(RecordingProvider)

    assert RecordingProvider.registered == ["registered"]
    assert RecordingProvider.booted == []

    with TestClient(app.fastapi):
        pass

    assert RecordingProvider.booted == ["booted"]


def test_container_resolves_the_application_itself(tmp_path: Path) -> None:
    make_project(tmp_path)
    container = Container()
    app = PyForge(base_path=tmp_path, container=container)

    assert container.make(PyForge) is app
