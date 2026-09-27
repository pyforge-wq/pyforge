"""PyForge — a batteries-included web framework for Python, built on
FastAPI.

Phases 1-3 provided the foundation, the database layer (``Model``, query
builder, migrations, factories/seeders), and the API layer (``FormRequest``,
``Resource``, centralized exception handling). Phases 4-6 add authentication
(``pyforge.auth``), caching, events, queues, scheduling, mail, notifications,
storage, and multi-tenancy (``pyforge.cache``/``events``/``queue``/
``scheduler``/``mail``/``notifications``/``storage``/``tenancy``) as
*optional* modules — none imported by this top-level ``pyforge`` import, and
none wired into ``PyForge`` automatically; see each module's own docstring
and ``docs/architecture/03-public-api-design.md``. Phase 7 adds
``pyforge.testing`` (fakes and assertion helpers), ``pyforge.security``
(rate limiting, secure headers), a generated-project ``Dockerfile``, and a
manual security hardening pass — see ``docs/architecture/10-security.md``
and ``docs/architecture/11-deployment.md``. See
``docs/architecture/09-roadmap.md`` for what's implemented vs. planned.
"""

from pyforge.config import Config, config, env
from pyforge.container import Container, container
from pyforge.core import PyForge, PyForgeError
from pyforge.orm import (
    Factory,
    Model,
    ModelNotFoundError,
    Paginator,
    QueryBuilder,
    Seeder,
    SoftDeletesMixin,
    TimestampsMixin,
    ULIDModel,
    UUIDModel,
    belongs_to,
    belongs_to_many,
    has_many,
    has_one,
)
from pyforge.providers import ServiceProvider
from pyforge.resources import Resource
from pyforge.routing import RouteGroup, Router
from pyforge.validation import FormRequest, validate

__version__ = "0.7.0"

__all__ = [
    "Config",
    "Container",
    "Factory",
    "FormRequest",
    "Model",
    "ModelNotFoundError",
    "Paginator",
    "PyForge",
    "PyForgeError",
    "QueryBuilder",
    "Resource",
    "RouteGroup",
    "Router",
    "Seeder",
    "ServiceProvider",
    "SoftDeletesMixin",
    "TimestampsMixin",
    "ULIDModel",
    "UUIDModel",
    "__version__",
    "belongs_to",
    "belongs_to_many",
    "config",
    "container",
    "env",
    "has_many",
    "has_one",
    "validate",
]
