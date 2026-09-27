from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import CacheDriver
from .drivers import FileCacheDriver, MemoryCacheDriver, RedisCacheDriver


class Cache:
    """The developer-facing cache API — a thin wrapper over whichever
    :class:`CacheDriver` was configured::

        Cache.get("users:1")
        Cache.put("users:1", user, ttl=300)
        Cache.remember("users:1", 300, lambda: User.find(1))
        Cache.forget("users:1")
    """

    def __init__(self, driver: CacheDriver) -> None:
        self.driver = driver

    def get(self, key: str, default: Any = None) -> Any:
        value = self.driver.get(key)
        return default if value is None else value

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.driver.put(key, value, ttl)

    def forget(self, key: str) -> None:
        self.driver.forget(key)

    def flush(self) -> None:
        self.driver.flush()

    def remember(self, key: str, ttl: int | None, callback: Callable[[], Any]) -> Any:
        cached = self.driver.get(key)
        if cached is not None:
            return cached
        value = callback()
        self.driver.put(key, value, ttl)
        return value


def make_cache(config: dict[str, Any]) -> Cache:
    """Builds a :class:`Cache` from the same shape as a generated project's
    ``config/cache.py``. Typically called once from a service provider's
    ``register()`` and bound into the container."""
    driver_name = config.get("default", "memory")

    if driver_name == "memory":
        return Cache(MemoryCacheDriver())

    if driver_name == "file":
        return Cache(FileCacheDriver(config.get("file_path", "storage/cache")))

    if driver_name == "redis":
        import redis

        client = redis.Redis.from_url(config.get("redis_url", "redis://127.0.0.1:6379/0"))
        return Cache(RedisCacheDriver(client))

    raise ValueError(f"Unknown cache driver '{driver_name}'.")
