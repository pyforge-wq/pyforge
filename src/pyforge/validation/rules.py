from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

RuleCheck = Callable[[Any, str | None, dict[str, Any]], str | None]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://[^\s]+$")


def _check_required(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    if value is None or value == "":
        return "This field is required."
    return None


def _check_nullable(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    return None


def _check_string(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    if value is not None and not isinstance(value, str):
        return "Must be a string."
    return None


def _check_integer(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    if value is not None and not isinstance(value, int):
        return "Must be an integer."
    return None


def _check_numeric(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    if value is not None and not isinstance(value, (int, float)):
        return "Must be a number."
    return None


def _check_boolean(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    if value is not None and not isinstance(value, bool):
        return "Must be a boolean."
    return None


def _check_email(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    if value is not None and not _EMAIL_RE.match(str(value)):
        return "Must be a valid email address."
    return None


def _check_url(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    if value is not None and not _URL_RE.match(str(value)):
        return "Must be a valid URL."
    return None


def _check_min(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    assert param is not None
    limit = float(param)
    size = len(value) if isinstance(value, (str, list, dict)) else value
    if size is not None and size < limit:
        return f"Must be at least {param}."
    return None


def _check_max(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    assert param is not None
    limit = float(param)
    size = len(value) if isinstance(value, (str, list, dict)) else value
    if size is not None and size > limit:
        return f"Must be at most {param}."
    return None


def _check_in(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    assert param is not None
    choices = param.split(",")
    if value is not None and str(value) not in choices:
        return f"Must be one of: {param}."
    return None


def _check_confirmed(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    return None  # handled specially by validate(), which knows the field name


def _check_unique(value: Any, param: str | None, data: dict[str, Any]) -> str | None:
    """``unique:table,column`` — checked lazily by :func:`validate` (needs an
    active database session and the ORM's shared metadata), not here."""
    return None


RULE_REGISTRY: dict[str, RuleCheck] = {
    "required": _check_required,
    "nullable": _check_nullable,
    "string": _check_string,
    "integer": _check_integer,
    "numeric": _check_numeric,
    "boolean": _check_boolean,
    "email": _check_email,
    "url": _check_url,
    "min": _check_min,
    "max": _check_max,
    "in": _check_in,
    "confirmed": _check_confirmed,
    "unique": _check_unique,
}


def _parse_rule(rule: str) -> tuple[str, str | None]:
    name, _, param = rule.partition(":")
    return name, (param or None)


def _is_present(value: Any) -> bool:
    return value is not None and value != ""


def _check_unique_constraint(field: str, value: Any, param: str) -> str | None:
    from sqlalchemy import select

    from pyforge.database import current_session
    from pyforge.orm import Base

    table_name, _, column = param.partition(",")
    column = column or field
    table = Base.metadata.tables.get(table_name)
    if table is None:
        raise ValueError(f"unique: rule references unknown table '{table_name}'.")
    exists = current_session().execute(
        select(table.c[column]).where(table.c[column] == value).limit(1)
    ).first()
    if exists is not None:
        return "Has already been taken."
    return None


def validate(data: dict[str, Any], rules: dict[str, str]) -> dict[str, list[str]]:
    """Runs pipe-separated ``rules`` (``"required|email"``)
    against ``data``. Returns ``{field: [messages]}`` for every field that
    failed at least one rule; an empty dict means validation passed."""
    errors: dict[str, list[str]] = {}

    for field, rule_string in rules.items():
        value = data.get(field)
        rule_names = rule_string.split("|")
        is_nullable = "nullable" in rule_names
        is_required = "required" in rule_names

        if not _is_present(value):
            if is_required:
                errors.setdefault(field, []).append("This field is required.")
            continue
        if not is_required and not is_nullable and value is None:
            continue

        for rule in rule_names:
            name, param = _parse_rule(rule)
            if name in ("required", "nullable"):
                continue
            if name == "confirmed":
                confirmation = data.get(f"{field}_confirmation")
                if value != confirmation:
                    errors.setdefault(field, []).append("Confirmation does not match.")
                continue
            if name == "unique":
                assert param is not None
                message = _check_unique_constraint(field, value, param)
                if message:
                    errors.setdefault(field, []).append(message)
                continue
            check = RULE_REGISTRY.get(name)
            if check is None:
                raise ValueError(f"Unknown validation rule '{name}'.")
            message = check(value, param, data)
            if message:
                errors.setdefault(field, []).append(message)

    return errors
