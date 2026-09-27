from unittest.mock import MagicMock

from typer.testing import CliRunner

from pyforge.console.cli import app
from pyforge.console.commands import package

runner = CliRunner()


def test_official_extra_installs_pyforge_framework_with_extra(monkeypatch) -> None:
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return MagicMock(returncode=0)

    monkeypatch.setattr(package.subprocess, "run", fake_run)

    result = runner.invoke(app, ["package:install", "auth"])

    assert result.exit_code == 0
    assert calls[0][-1] == "pyforge-framework[auth]"


def test_pyforge_prefixed_name_installs_as_is(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(package.subprocess, "run", lambda args, **kw: calls.append(args) or MagicMock(returncode=0))

    runner.invoke(app, ["package:install", "pyforge-stripe"])

    assert calls[0][-1] == "pyforge-stripe"


def test_bare_name_gets_pyforge_prefix(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(package.subprocess, "run", lambda args, **kw: calls.append(args) or MagicMock(returncode=0))

    runner.invoke(app, ["package:install", "stripe"])

    assert calls[0][-1] == "pyforge-stripe"


def test_nonzero_exit_code_propagates(monkeypatch) -> None:
    monkeypatch.setattr(package.subprocess, "run", lambda args, **kw: MagicMock(returncode=1))

    result = runner.invoke(app, ["package:install", "stripe"])

    assert result.exit_code == 1
