from __future__ import annotations

import os
from pathlib import Path
from typing import Any, overload

from dotenv import dotenv_values

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}

_loaded_files: set[Path] = set()


def load_env(path: str | Path = ".env") -> None:
    """Load a dotenv file into ``os.environ`` without overriding variables
    that are already set in the real process environment."""
    resolved = Path(path).resolve()
    values = dotenv_values(resolved)
    for key, value in values.items():
        if key not in os.environ and value is not None:
            os.environ[key] = value
    _loaded_files.add(resolved)


def _cast(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    if lowered in ("null", "none", ""):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


@overload
def env(key: str) -> Any: ...
@overload
def env(key: str, default: Any) -> Any: ...


def env(key: str, default: Any = None) -> Any:
    """Read an environment variable, casting common literals
    (``true``/``false``/``null``/numbers) to their real Python types."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    return _cast(raw)
