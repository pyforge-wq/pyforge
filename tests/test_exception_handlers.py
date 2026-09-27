from pathlib import Path

from fastapi.testclient import TestClient

from pyforge import PyForge, Router
from pyforge.container import Container
from pyforge.core import PyForgeError
from pyforge.orm import ModelNotFoundError


class ExplodingController:
    async def not_found(self) -> None:
        raise ModelNotFoundError("No User found with primary key 999.")

    async def broken(self) -> None:
        raise PyForgeError("something internal broke")


def make_app(tmp_path: Path, *, debug: bool) -> PyForge:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "app.py").write_text(f'config = {{"debug": {debug!r}}}\n')
    app = PyForge(base_path=tmp_path, container=Container())
    router = Router(container=app.container)
    router.get("/missing", ExplodingController.not_found)
    router.get("/broken", ExplodingController.broken)
    app.register_routes(router)
    return app


def test_model_not_found_error_becomes_404(tmp_path: Path) -> None:
    app = make_app(tmp_path, debug=False)
    with TestClient(app.fastapi, raise_server_exceptions=False) as client:
        response = client.get("/missing")
    assert response.status_code == 404
    assert "999" in response.json()["message"]


def test_pyforge_error_becomes_500_with_generic_message_when_not_debug(tmp_path: Path) -> None:
    app = make_app(tmp_path, debug=False)
    with TestClient(app.fastapi, raise_server_exceptions=False) as client:
        response = client.get("/broken")
    assert response.status_code == 500
    assert response.json() == {"message": "Internal Server Error"}


def test_pyforge_error_includes_detail_when_debug(tmp_path: Path) -> None:
    app = make_app(tmp_path, debug=True)
    with TestClient(app.fastapi, raise_server_exceptions=False) as client:
        response = client.get("/broken")
    assert response.status_code == 500
    assert response.json() == {"message": "something internal broke"}
