from typing import ClassVar

import fakeredis
import pytest

from pyforge.queue import (
    Job,
    RedisQueueDriver,
    SyncQueueDriver,
    Worker,
    default_queue,
    dispatch,
    make_queue,
    set_default_queue,
)

# Module-level, not instance-level: a Job is pickled to go through the Redis
# driver, which copies instance attributes by value — an instance-level list
# would silently stop being the same object after a pop(). A module-level
# list survives because unpickling re-uses this already-imported module's
# namespace rather than recreating it. Cleared at the top of every test that
# uses it.
_LOG: list[str] = []
_ATTEMPTS: list[int] = []


class RecordResult(Job):
    def __init__(self, value: str) -> None:
        self.value = value

    def handle(self) -> None:
        _LOG.append(self.value)


class AlwaysFails(Job):
    max_retries: ClassVar[int] = 2
    retry_backoff_seconds: ClassVar[float] = 0

    def handle(self) -> None:
        _ATTEMPTS.append(1)
        raise ValueError("boom")


class FailsTwiceThenSucceeds(Job):
    max_retries: ClassVar[int] = 3
    retry_backoff_seconds: ClassVar[float] = 0

    def handle(self) -> None:
        _ATTEMPTS.append(1)
        if len(_ATTEMPTS) < 3:
            raise ValueError("not yet")


def test_sync_driver_runs_job_immediately_on_push() -> None:
    _LOG.clear()
    driver = SyncQueueDriver()
    driver.push(RecordResult("done"))
    assert _LOG == ["done"]


def test_sync_driver_pop_always_returns_none() -> None:
    driver = SyncQueueDriver()
    assert driver.pop() is None


def test_redis_driver_push_and_pop_roundtrip() -> None:
    _LOG.clear()
    driver = RedisQueueDriver(fakeredis.FakeRedis())
    driver.push(RecordResult("hello"))

    job = driver.pop(timeout=1)
    assert job is not None
    assert _LOG == []  # not run yet — pop only retrieves it
    job.handle()
    assert _LOG == ["hello"]


def test_redis_driver_pop_returns_none_when_empty() -> None:
    driver = RedisQueueDriver(fakeredis.FakeRedis())
    assert driver.pop(timeout=1) is None


def test_redis_driver_priority_queues() -> None:
    _LOG.clear()
    driver = RedisQueueDriver(fakeredis.FakeRedis())
    driver.push(RecordResult("low-priority"), queue="low")
    driver.push(RecordResult("high-priority"), queue="high")

    job = driver.pop(queues=["high", "low"], timeout=1)
    assert job is not None
    job.handle()
    assert _LOG == ["high-priority"]


def test_worker_run_once_processes_a_job() -> None:
    _LOG.clear()
    driver = RedisQueueDriver(fakeredis.FakeRedis())
    driver.push(RecordResult("value"))

    worker = Worker(driver)
    assert worker.run_once(timeout=1) is True
    assert _LOG == ["value"]
    assert worker.run_once(timeout=1) is False


def test_worker_retries_up_to_max_retries_then_calls_on_failure() -> None:
    _ATTEMPTS.clear()
    driver = RedisQueueDriver(fakeredis.FakeRedis())
    failures: list = []
    driver.push(AlwaysFails())

    worker = Worker(driver, on_failure=lambda job, exc: failures.append(str(exc)))
    worker.run_once(timeout=1)

    assert len(_ATTEMPTS) == 3  # 1 initial + 2 retries
    assert failures == ["boom"]


def test_worker_succeeds_after_transient_failures() -> None:
    _ATTEMPTS.clear()
    driver = RedisQueueDriver(fakeredis.FakeRedis())
    failures: list = []
    driver.push(FailsTwiceThenSucceeds())

    worker = Worker(driver, on_failure=lambda job, exc: failures.append(exc))
    worker.run_once(timeout=1)

    assert len(_ATTEMPTS) == 3
    assert failures == []


def test_worker_work_processes_up_to_max_jobs() -> None:
    _LOG.clear()
    driver = RedisQueueDriver(fakeredis.FakeRedis())
    for i in range(3):
        driver.push(RecordResult(str(i)))

    worker = Worker(driver)
    processed = worker.work(timeout=1, max_jobs=3)

    assert processed == 3
    assert _LOG == ["0", "1", "2"]


def test_make_queue_sync() -> None:
    assert isinstance(make_queue({"default": "sync"}), SyncQueueDriver)


def test_make_queue_unknown_driver_raises() -> None:
    with pytest.raises(ValueError):
        make_queue({"default": "not-a-driver"})


def test_dispatch_uses_default_queue() -> None:
    _LOG.clear()
    driver = SyncQueueDriver()
    set_default_queue(driver)
    try:
        dispatch(RecordResult("via-dispatch"))
        assert _LOG == ["via-dispatch"]
    finally:
        import pyforge.queue.queue as queue_module

        queue_module._default_driver = None


def test_default_queue_raises_when_unset() -> None:
    import pyforge.queue.queue as queue_module

    queue_module._default_driver = None
    with pytest.raises(RuntimeError):
        default_queue()
