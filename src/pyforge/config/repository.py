from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


class Config:
    """Dot-notation configuration store.

    Namespaces (``app``, ``database``, ``auth``, ...) come from files under
    the project's ``config/`` directory, each exposing a module-level
    ``config: dict`` — plain Python instead of a config DSL.
    """

    def __init__(self, items: dict[str, Any] | None = None) -> None:
        self._items: dict[str, Any] = items or {}

    @classmethod
    def load_directory(cls, directory: str | Path) -> Config:
        directory = Path(directory)
        items: dict[str, Any] = {}
        if directory.is_dir():
            for file in sorted(directory.glob("*.py")):
                if file.stem.startswith("_"):
                    continue
                items[file.stem] = cls._load_module_config(file)
        return cls(items)

    @staticmethod
    def _load_module_config(file: Path) -> dict[str, Any]:
        spec = importlib.util.spec_from_file_location(f"pyforge_config_{file.stem}", file)
        if spec is None or spec.loader is None:
            return {}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "config", {})

    def get(self, key: str, default: Any = None) -> Any:
        node: Any = self._items
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, key: str, value: Any) -> None:
        parts = key.split(".")
        node = self._items
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def all(self) -> dict[str, Any]:
        return self._items

    def __contains__(self, key: str) -> bool:
        sentinel = object()
        return self.get(key, sentinel) is not sentinel
