from __future__ import annotations

import re


def to_pascal_case(name: str) -> str:
    parts = re.split(r"[-_\s]+", name.strip())
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def to_snake_case(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.replace("-", "_").replace(" ", "_").lower()


def to_kebab_case(name: str) -> str:
    return to_snake_case(name).replace("_", "-")


def class_name_with_suffix(raw: str, suffix: str) -> str:
    """Normalize ``raw`` to PascalCase and ensure it ends with ``suffix``
    (e.g. ``"user"`` + ``"Controller"`` -> ``"UserController"``, while
    ``"UserController"`` is left as-is)."""
    pascal = to_pascal_case(raw)
    return pascal if pascal.endswith(suffix) else f"{pascal}{suffix}"
