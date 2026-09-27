from __future__ import annotations

from typing import Any

from pyforge.events import EventDispatcher
from pyforge.queue import Job, QueueDriver


class FakeQueueDriver(QueueDriver):
    """Records pushed jobs instead of running them — swap in with
    :func:`fake_queue`, then assert against `.pushed` (or use
    `.assert_pushed`/`.assert_not_pushed`). The queue counterpart to
    :class:`pyforge.mail.ArrayMailDriver`."""

    def __init__(self) -> None:
        self.pushed: list[tuple[Job, str | None]] = []

    def push(self, job: Job, *, queue: str | None = None) -> None:
        self.pushed.append((job, queue))

    def pop(self, *, queues: list[str] | None = None, timeout: int = 5) -> Job | None:
        return None

    def assert_pushed(self, job_class: type[Job]) -> None:
        if not any(isinstance(job, job_class) for job, _ in self.pushed):
            raise AssertionError(f"{job_class.__name__} was not pushed.")

    def assert_not_pushed(self, job_class: type[Job]) -> None:
        if any(isinstance(job, job_class) for job, _ in self.pushed):
            raise AssertionError(f"{job_class.__name__} was pushed, expected it not to be.")


class FakeEventDispatcher(EventDispatcher):
    """Records dispatched events instead of running their listeners — swap
    in with :func:`fake_events`. Useful when a test wants to assert
    "this action fired that event" without also exercising (and needing
    the dependencies of) every listener registered for it."""

    def __init__(self) -> None:
        super().__init__()
        self.dispatched: list[Any] = []

    async def dispatch(self, event: object) -> None:
        self.dispatched.append(event)

    def assert_dispatched(self, event_type: type) -> None:
        if not any(isinstance(evt, event_type) for evt in self.dispatched):
            raise AssertionError(f"{event_type.__name__} was not dispatched.")

    def assert_not_dispatched(self, event_type: type) -> None:
        if any(isinstance(evt, event_type) for evt in self.dispatched):
            raise AssertionError(f"{event_type.__name__} was dispatched, expected it not to be.")
