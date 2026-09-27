from __future__ import annotations

from typing import Any


class CacheDriver:
    """Base class for cache drivers — see :class:`MemoryCacheDriver`,
    :class:`FileCacheDriver`, :class:`RedisCacheDriver`."""

    def get(self, key: str) -> Any:
        raise NotImplementedError

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        raise NotImplementedError

    def forget(self, key: str) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError
