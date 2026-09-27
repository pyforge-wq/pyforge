from __future__ import annotations

import time
from collections.abc import Callable

from .drivers import QueueDriver
from .job import Job


class Worker:
    """Pops jobs off a :class:`QueueDriver` and runs them, retrying up to
    ``job.max_retries`` times (sleeping ``job.retry_backoff_seconds`` between
    attempts) before giving up. ``pyforge queue:work`` drives this in a
    loop; it's also usable directly in tests without a CLI process."""

    def __init__(self, driver: QueueDriver, *, on_failure: Callable[[Job, Exception], None] | None = None) -> None:
        self.driver = driver
        self.on_failure = on_failure

    def run_once(self, *, queues: list[str] | None = None, timeout: int = 5) -> bool:
        """Pops and runs a single job. Returns ``False`` if none was
        available within ``timeout`` seconds."""
        job = self.driver.pop(queues=queues, timeout=timeout)
        if job is None:
            return False
        self._run_with_retries(job)
        return True

    def _run_with_retries(self, job: Job) -> None:
        attempt = 1
        while True:
            try:
                job.handle()
                return
            except Exception as exc:  # noqa: BLE001 - a job's own failure must not crash the worker
                if attempt > job.max_retries:
                    if self.on_failure is not None:
                        self.on_failure(job, exc)
                    return
                if job.retry_backoff_seconds:
                    time.sleep(job.retry_backoff_seconds)
                attempt += 1

    def work(self, *, queues: list[str] | None = None, timeout: int = 5, max_jobs: int | None = None) -> int:
        """Runs until ``max_jobs`` have been processed, or forever if
        ``max_jobs`` is ``None`` (the real ``queue:work`` use case — stop it
        with Ctrl+C). Returns the number of jobs actually run."""
        processed = 0
        while max_jobs is None or processed < max_jobs:
            if self.run_once(queues=queues, timeout=timeout):
                processed += 1
        return processed
