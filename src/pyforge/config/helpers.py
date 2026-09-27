from __future__ import annotations

from typing import Any

from .repository import Config

_active_config: Config | None = None


def set_active_config(config: Config | None) -> None:
    """Called by :class:`pyforge.core.Application` on construction so the
    module-level ``config()`` helper has something to read from."""
    global _active_config
    _active_config = config


def config(key: str | None = None, default: Any = None) -> Any:
    """A global config accessor: ``config("app.name")``.

    With no key, returns the whole :class:`Config` repository. Requires an
    active :class:`~pyforge.core.Application` to have been constructed first.
    """
    if _active_config is None:
        raise RuntimeError(
            "No active PyForge application. Construct a PyForge() app before calling config()."
        )
    if key is None:
        return _active_config
    return _active_config.get(key, default)
