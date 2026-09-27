from datetime import datetime

import pytest

from pyforge.scheduler import Schedule, make_cron_check


class RecordingJob:
    def __init__(self) -> None:
        self.calls = 0

    def handle(self) -> None:
        self.calls += 1


def test_every_minute_is_always_due() -> None:
    schedule = Schedule()
    job = RecordingJob()
    schedule.every_minute(job)

    schedule.run_due(datetime(2026, 1, 1, 13, 27))
    assert job.calls == 1


def test_every_hour_only_due_at_minute_zero() -> None:
    schedule = Schedule()
    job = RecordingJob()
    schedule.every_hour(job)

    assert schedule.due_tasks(datetime(2026, 1, 1, 13, 30)) == []
    schedule.run_due(datetime(2026, 1, 1, 13, 0))
    assert job.calls == 1


def test_every_day_defaults_to_midnight() -> None:
    schedule = Schedule()
    job = RecordingJob()
    schedule.every_day(job)

    assert schedule.due_tasks(datetime(2026, 1, 1, 9, 0)) == []
    schedule.run_due(datetime(2026, 1, 1, 0, 0))
    assert job.calls == 1


def test_every_day_at_specific_time() -> None:
    schedule = Schedule()
    job = RecordingJob()
    schedule.every_day(job).at("02:30")

    assert schedule.due_tasks(datetime(2026, 1, 1, 0, 0)) == []
    schedule.run_due(datetime(2026, 1, 1, 2, 30))
    assert job.calls == 1


def test_callable_job_without_handle_method_works() -> None:
    schedule = Schedule()
    calls = []
    schedule.every_minute(lambda: calls.append(1))
    schedule.run_due(datetime(2026, 1, 1, 0, 0))
    assert calls == [1]


def test_unrunnable_job_raises() -> None:
    schedule = Schedule()
    task = schedule.every_minute(object())
    with pytest.raises(TypeError):
        task.run()


def test_run_due_returns_only_tasks_that_ran() -> None:
    schedule = Schedule()
    hourly_job = RecordingJob()
    minutely_job = RecordingJob()
    schedule.every_hour(hourly_job)
    schedule.every_minute(minutely_job)

    ran = schedule.run_due(datetime(2026, 1, 1, 13, 30))
    assert len(ran) == 1
    assert minutely_job.calls == 1
    assert hourly_job.calls == 0


# --- cron expression parsing ---


def test_cron_wildcard_matches_every_minute() -> None:
    check = make_cron_check("* * * * *")
    assert check(datetime(2026, 1, 1, 13, 27))


def test_cron_exact_minute_and_hour() -> None:
    check = make_cron_check("30 2 * * *")
    assert check(datetime(2026, 1, 1, 2, 30))
    assert not check(datetime(2026, 1, 1, 2, 31))
    assert not check(datetime(2026, 1, 1, 3, 30))


def test_cron_step_syntax() -> None:
    check = make_cron_check("*/15 * * * *")
    assert check(datetime(2026, 1, 1, 0, 0))
    assert check(datetime(2026, 1, 1, 0, 15))
    assert check(datetime(2026, 1, 1, 0, 30))
    assert not check(datetime(2026, 1, 1, 0, 10))


def test_cron_range_syntax() -> None:
    check = make_cron_check("0 9-17 * * *")
    assert check(datetime(2026, 1, 1, 9, 0))
    assert check(datetime(2026, 1, 1, 17, 0))
    assert not check(datetime(2026, 1, 1, 18, 0))


def test_cron_list_syntax() -> None:
    check = make_cron_check("0 0 1,15 * *")
    assert check(datetime(2026, 1, 1, 0, 0))
    assert check(datetime(2026, 1, 15, 0, 0))
    assert not check(datetime(2026, 1, 2, 0, 0))


def test_cron_weekday_sunday_is_zero() -> None:
    # 2026-01-04 is a Sunday
    check = make_cron_check("0 0 * * 0")
    assert check(datetime(2026, 1, 4, 0, 0))
    assert not check(datetime(2026, 1, 5, 0, 0))  # Monday


def test_cron_invalid_field_count_raises() -> None:
    with pytest.raises(ValueError):
        make_cron_check("* * * *")


def test_schedule_cron_integration() -> None:
    schedule = Schedule()
    job = RecordingJob()
    schedule.cron("0 3 * * *", job)

    assert schedule.due_tasks(datetime(2026, 1, 1, 3, 1)) == []
    schedule.run_due(datetime(2026, 1, 1, 3, 0))
    assert job.calls == 1
