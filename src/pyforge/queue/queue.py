from __future__ import annotations

from typing import Any

from .drivers import QueueDriver, RedisQueueDriver, SyncQueueDriver
from .job import Job

_default_driver: QueueDriver | None = None


def set_default_queue(driver: QueueDriver) -> None:
    """Registers the process-wide default queue driver — typically from a
    service provider's ``register()``, right after :func:`make_queue`."""
    global _default_driver
    _default_driver = driver


def default_queue() -> QueueDriver:
    if _default_driver is None:
        raise RuntimeError(
            "No default queue configured. Call set_default_queue(make_queue(config('queue'))) "
            "once, e.g. from a service provider's register()."
        )
    return _default_driver


def dispatch(job: Job, *, queue: str | None = None) -> None:
    """``dispatch(SendWelcomeEmail(user.id))`` — pushes to the default
    queue driver (or runs it immediately, for the sync driver)."""
    default_queue().push(job, queue=queue)


def make_queue(config: dict[str, Any]) -> QueueDriver:
    """Builds a :class:`QueueDriver` from the same shape as a generated
    project's ``config/queue.py``."""
    driver_name = config.get("default", "sync")

    if driver_name == "sync":
        return SyncQueueDriver()

    if driver_name == "redis":
        import redis

        client = redis.Redis.from_url(config.get("redis_url", "redis://127.0.0.1:6379/0"))
        return RedisQueueDriver(client)

    raise ValueError(f"Unknown queue driver '{driver_name}'.")
