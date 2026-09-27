import pytest
from sqlalchemy import text

from pyforge.database import DatabaseManager, current_session, session_scope, set_current_database


def make_manager(tmp_path) -> DatabaseManager:
    return DatabaseManager(
        {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": str(tmp_path / "test.sqlite")},
            },
        }
    )


def test_sqlite_connection_url(tmp_path) -> None:
    manager = make_manager(tmp_path)
    assert manager.connection_url() == f"sqlite:///{tmp_path / 'test.sqlite'}"


def test_mysql_connection_url() -> None:
    manager = DatabaseManager(
        {
            "default": "mysql",
            "connections": {
                "mysql": {
                    "driver": "mysql",
                    "host": "127.0.0.1",
                    "port": 3306,
                    "database": "app",
                    "username": "root",
                    "password": "s3cr3t",
                },
            },
        }
    )
    assert manager.connection_url() == "mysql+pymysql://root:s3cr3t@127.0.0.1:3306/app"


def test_unknown_connection_name_raises(tmp_path) -> None:
    manager = make_manager(tmp_path)
    with pytest.raises(KeyError):
        manager.connection_url("does-not-exist")


def test_session_scope_commits_on_success(tmp_path) -> None:
    manager = make_manager(tmp_path)
    set_current_database(manager)
    try:
        with session_scope() as session:
            session.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))
            session.execute(text("INSERT INTO t (id) VALUES (1)"))

        with session_scope() as session:
            count = session.execute(text("SELECT COUNT(*) FROM t")).scalar()
        assert count == 1
    finally:
        set_current_database(None)
        manager.dispose()


def test_session_scope_rolls_back_on_exception(tmp_path) -> None:
    manager = make_manager(tmp_path)
    set_current_database(manager)
    try:
        with session_scope() as session:
            session.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))

        with pytest.raises(ValueError), session_scope() as session:
            session.execute(text("INSERT INTO t (id) VALUES (1)"))
            raise ValueError("boom")

        with session_scope() as session:
            count = session.execute(text("SELECT COUNT(*) FROM t")).scalar()
        assert count == 0
    finally:
        set_current_database(None)
        manager.dispose()


def test_current_session_raises_outside_scope() -> None:
    with pytest.raises(RuntimeError):
        current_session()
