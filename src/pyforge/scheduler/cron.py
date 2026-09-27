from __future__ import annotations

from collections.abc import Callable
from datetime import datetime


def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    values: set[int] = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step_str = part.split("/")
            step = int(step_str)
        if part == "*":
            start, end = min_val, max_val
        elif "-" in part:
            start_str, end_str = part.split("-")
            start, end = int(start_str), int(end_str)
        else:
            start = end = int(part)
        values.update(range(start, end + 1, step))
    return values


def make_cron_check(expression: str) -> Callable[[datetime], bool]:
    """Parses a standard 5-field cron expression (``minute hour day month
    weekday``, ``*``/``N``/``N-M``/``N,M``/``*/N`` in each field, Sunday=0)
    into a ``now -> bool`` predicate."""
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"Cron expression must have 5 fields, got {len(fields)}: '{expression}'")

    minute_set = _parse_cron_field(fields[0], 0, 59)
    hour_set = _parse_cron_field(fields[1], 0, 23)
    day_set = _parse_cron_field(fields[2], 1, 31)
    month_set = _parse_cron_field(fields[3], 1, 12)
    weekday_set = _parse_cron_field(fields[4], 0, 6)

    def check(now: datetime) -> bool:
        cron_weekday = (now.weekday() + 1) % 7  # Python: Mon=0..Sun=6 -> cron: Sun=0..Sat=6
        return (
            now.minute in minute_set
            and now.hour in hour_set
            and now.day in day_set
            and now.month in month_set
            and cron_weekday in weekday_set
        )

    return check
