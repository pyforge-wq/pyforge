from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from .cron import make_cron_check

DueCheck = Callable[[datetime], bool]


class ScheduledTask:
    """One entry in a :class:`Schedule` — returned by ``schedule.every_day(...)``
    etc. so a frequency helper can be refined further, e.g.
    ``schedule.every_day(job).at("02:00")``."""

    def __init__(self, job: Any, due_check: DueCheck) -> None:
        self.job = job
        self._due_check = due_check

    def at(self, time_str: str) -> ScheduledTask:
        """Only meaningful after ``every_day(...)`` — refines it to a
        specific ``HH:MM`` instead of midnight."""
        hour_str, minute_str = time_str.split(":")
        hour, minute = int(hour_str), int(minute_str)
        self._due_check = lambda now: now.hour == hour and now.minute == minute
        return self

    def is_due(self, now: datetime) -> bool:
        return self._due_check(now)

    def run(self) -> None:
        handler = getattr(self.job, "handle", None)
        if handler is not None:
            handler()
        elif callable(self.job):
            self.job()
        else:
            raise TypeError(f"{self.job!r} is not runnable — give it a handle() method, or make it callable.")


class Schedule:
    """A registry of scheduled tasks, checked (not run continuously) each
    time ``pyforge schedule:run`` executes — the standard cron-driven-scheduler
    design: a real OS cron entry invokes ``schedule:run`` every minute, and each
    task's frequency helper decides whether *this* minute is a match, e.g.
    ``every_hour`` matches when ``now.minute == 0``. There's no persistent
    "last run" state to manage — the external once-a-minute cadence plus
    each task's own time-of-day check is sufficient, and is exactly what
    keeps this a stateless, restart-safe design::

        schedule = Schedule()
        schedule.every_day(GenerateReports()).at("02:00")
        schedule.every_hour(CleanupTemporaryFiles())
        schedule.cron("*/15 * * * *", SyncExternalData())
    """

    def __init__(self) -> None:
        self._tasks: list[ScheduledTask] = []

    def _add(self, job: Any, due_check: DueCheck) -> ScheduledTask:
        task = ScheduledTask(job, due_check)
        self._tasks.append(task)
        return task

    def every_minute(self, job: Any) -> ScheduledTask:
        return self._add(job, lambda now: True)

    def every_hour(self, job: Any) -> ScheduledTask:
        return self._add(job, lambda now: now.minute == 0)

    def every_day(self, job: Any) -> ScheduledTask:
        """Defaults to midnight; chain ``.at("HH:MM")`` for another time."""
        return self._add(job, lambda now: now.hour == 0 and now.minute == 0)

    def cron(self, expression: str, job: Any) -> ScheduledTask:
        return self._add(job, make_cron_check(expression))

    def due_tasks(self, now: datetime | None = None) -> list[ScheduledTask]:
        now = now or datetime.now()
        return [task for task in self._tasks if task.is_due(now)]

    def run_due(self, now: datetime | None = None) -> list[ScheduledTask]:
        """Runs every currently-due task and returns the list of tasks that ran."""
        due = self.due_tasks(now)
        for task in due:
            task.run()
        return due
