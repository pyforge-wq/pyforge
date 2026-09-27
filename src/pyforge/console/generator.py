from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import jinja2

STUBS_DIR = Path(__file__).parent / "stubs"
PROJECT_TEMPLATE_DIR = STUBS_DIR / "project"

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(STUBS_DIR)),
    keep_trailing_newline=True,
)


def render_stub(relative_path: str, context: dict[str, Any]) -> str:
    template = _env.get_template(relative_path.replace("\\", "/"))
    return template.render(**context)


def write_stub(relative_path: str, destination: Path, context: dict[str, Any]) -> Path:
    if destination.exists():
        raise FileExistsError(f"'{destination}' already exists.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_stub(relative_path, context))
    return destination


def scaffold_project(destination: Path, *, project_name: str) -> None:
    """Copy the ``stubs/project`` template tree into ``destination``,
    rendering every ``*.stub`` file with Jinja2 and stripping the
    ``.stub`` suffix from its final filename."""
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Directory '{destination}' already exists and is not empty.")
    destination.mkdir(parents=True, exist_ok=True)

    # A real, per-project random secret in .env (never committed) — not a
    # static "change-me" a fresh project might accidentally ship to
    # production unchanged. .env.example keeps a placeholder instead, since
    # that file *is* meant to be committed and shared.
    context = {"project_name": project_name, "jwt_secret": secrets.token_urlsafe(32)}

    for template_path in sorted(PROJECT_TEMPLATE_DIR.rglob("*.stub")):
        relative_to_project = template_path.relative_to(PROJECT_TEMPLATE_DIR)
        relative_to_stubs_root = template_path.relative_to(STUBS_DIR)
        target = destination / relative_to_project.with_suffix("")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_stub(str(relative_to_stubs_root), context))
