from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from pyforge import PyForge, Router
from pyforge.container import Container
from pyforge.database import set_current_database
from pyforge.orm import Base, Model


class IntegrationWidget(Model):
    __tablename__ = "integration_test_widgets"

    name: Mapped[str] = mapped_column(String(255))


class WidgetController:
    async def store(self) -> dict:
        widget = IntegrationWidget.create(name="from-request")
        return {"id": widget.id, "name": widget.name}

    async def index(self) -> list[dict]:
        return [{"id": w.id, "name": w.name} for w in IntegrationWidget.all()]

    async def store_then_fail(self) -> None:
        IntegrationWidget.create(name="should-not-persist")
        raise ValueError("boom")


def make_app(tmp_path: Path) -> PyForge:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "app.py").write_text('config = {"name": "Test App"}\n')
    db_path = tmp_path / "db.sqlite"
    (tmp_path / "config" / "database.py").write_text(
        "config = {\n"
        '    "default": "sqlite",\n'
        '    "connections": {"sqlite": {"driver": "sqlite", "database": "'
        + str(db_path).replace("\\", "\\\\")
        + '"}},\n'
        "}\n"
    )
    app = PyForge(base_path=tmp_path, container=Container())
    assert app.database is not None
    Base.metadata.create_all(app.database.engine())
    return app


def teardown(app: PyForge) -> None:
    assert app.database is not None
    app.database.dispose()
    set_current_database(None)


def test_model_works_in_a_controller_with_zero_explicit_wiring(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    try:
        router = Router(container=app.container)
        router.post("/widgets", WidgetController.store)
        router.get("/widgets", WidgetController.index)
        app.register_routes(router)

        with TestClient(app.fastapi) as client:
            response = client.post("/widgets")
            assert response.status_code == 200
            assert response.json()["name"] == "from-request"

            response = client.get("/widgets")
            assert response.json() == [{"id": 1, "name": "from-request"}]
    finally:
        teardown(app)


def test_request_session_rolls_back_when_the_handler_raises(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    try:
        router = Router(container=app.container)
        router.post("/widgets/fail", WidgetController.store_then_fail)
        router.get("/widgets", WidgetController.index)
        app.register_routes(router)

        with TestClient(app.fastapi, raise_server_exceptions=False) as client:
            response = client.post("/widgets/fail")
            assert response.status_code == 500

            response = client.get("/widgets")
            assert response.json() == []
    finally:
        teardown(app)
