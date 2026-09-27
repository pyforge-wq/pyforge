from pathlib import Path

from pyforge.config import Config, env


def test_load_directory_reads_namespaced_config_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text('config = {"name": "Demo", "debug": True}\n')
    (tmp_path / "database.py").write_text('config = {"default": "sqlite"}\n')

    repository = Config.load_directory(tmp_path)

    assert repository.get("app.name") == "Demo"
    assert repository.get("app.debug") is True
    assert repository.get("database.default") == "sqlite"


def test_get_returns_default_for_missing_key() -> None:
    repository = Config({"app": {"name": "Demo"}})
    assert repository.get("app.missing", "fallback") == "fallback"
    assert repository.get("missing.namespace") is None


def test_set_creates_nested_path() -> None:
    repository = Config()
    repository.set("cache.default", "redis")
    assert repository.get("cache.default") == "redis"


def test_contains() -> None:
    repository = Config({"app": {"name": "Demo"}})
    assert "app.name" in repository
    assert "app.missing" not in repository


def test_env_casts_common_literals(monkeypatch) -> None:
    monkeypatch.setenv("PYFORGE_TEST_BOOL", "true")
    monkeypatch.setenv("PYFORGE_TEST_INT", "42")
    monkeypatch.setenv("PYFORGE_TEST_NULL", "null")

    assert env("PYFORGE_TEST_BOOL") is True
    assert env("PYFORGE_TEST_INT") == 42
    assert env("PYFORGE_TEST_NULL") is None
    assert env("PYFORGE_TEST_MISSING", "default") == "default"
