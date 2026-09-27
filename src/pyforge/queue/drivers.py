from __future__ import annotations

import pickle
from typing import Any

from .job import Job


class QueueDriver:
    def push(self, job: Job, *, queue: str | None = None) -> None:
        raise NotImplementedError

    def pop(self, *, queues: list[str] | None = None, timeout: int = 5) -> Job | None:
        raise NotImplementedError


class SyncQueueDriver(QueueDriver):
    """Runs a job immediately, in-process, when pushed — no worker needed.
    The default for local development and tests. ``pop()`` always returns
    ``None``: nothing is ever actually queued, so there's nothing for
    ``pyforge queue:work`` to pick up."""

    def push(self, job: Job, *, queue: str | None = None) -> None:
        job.handle()

    def pop(self, *, queues: list[str] | None = None, timeout: int = 5) -> Job | None:
        return None


class RedisQueueDriver(QueueDriver):
    """Backed by a real ``redis.Redis`` client. Jobs are pickled onto a list
    per queue name; ``pop`` uses ``BLPOP`` across multiple queue names in
    priority order (first name wins when both have work), driven by
    ``--queue=high,default,low``."""

    def __init__(self, client: Any, default_queue: str = "default") -> None:
        self.client = client
        self.default_queue = default_queue

    def push(self, job: Job, *, queue: str | None = None) -> None:
        self.client.rpush(queue or self.default_queue, pickle.dumps(job))

    def pop(self, *, queues: list[str] | None = None, timeout: int = 5) -> Job | None:
        result = self.client.blpop(queues or [self.default_queue], timeout=timeout)
        if result is None:
            return None
        _, raw = result
        job = pickle.loads(raw)
        if not isinstance(job, Job):
            raise TypeError(f"Expected a Job on the queue, got {type(job)!r}.")
        return job
