from __future__ import annotations

import hashlib
import pickle
import threading
import time
from pathlib import Path
from typing import Any

from .base import CacheDriver


class MemoryCacheDriver(CacheDriver):
    """An in-process dict with per-key expiry. Gone on restart, and not
    shared across worker processes — the default for local development,
    not for anything running with more than one process."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and expires_at < time.time():
                del self._store[key]
                return None
            return value

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.time() + ttl if ttl is not None else None
        with self._lock:
            self._store[key] = (value, expires_at)

    def forget(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def flush(self) -> None:
        with self._lock:
            self._store.clear()


class FileCacheDriver(CacheDriver):
    """Pickles ``(value, expires_at)`` per key into a directory — survives a
    restart, shared across processes on the same filesystem, still not a
    good fit for multiple machines (use the Redis driver there)."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.cache"

    def get(self, key: str) -> Any:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            value, expires_at = pickle.loads(path.read_bytes())
        except (pickle.PickleError, EOFError, ValueError):
            path.unlink(missing_ok=True)
            return None
        if expires_at is not None and expires_at < time.time():
            path.unlink(missing_ok=True)
            return None
        return value

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.time() + ttl if ttl is not None else None
        self._path_for(key).write_bytes(pickle.dumps((value, expires_at)))

    def forget(self, key: str) -> None:
        self._path_for(key).unlink(missing_ok=True)

    def flush(self) -> None:
        for file in self.directory.glob("*.cache"):
            file.unlink(missing_ok=True)


class RedisCacheDriver(CacheDriver):
    """Backed by a real ``redis.Redis`` client — values are pickled. The
    only driver here that's actually shared across processes/machines.
    ``flush()`` calls ``FLUSHDB`` — point ``redis_url`` at a dedicated
    database index for the cache in production, not one shared with the
    queue driver or anything else.
    """

    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, key: str) -> Any:
        raw = self.client.get(key)
        if raw is None:
            return None
        return pickle.loads(raw)

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.client.set(key, pickle.dumps(value), ex=ttl)

    def forget(self, key: str) -> None:
        self.client.delete(key)

    def flush(self) -> None:
        self.client.flushdb()
