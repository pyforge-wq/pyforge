"""Multi-tenancy — an *optional* module (``pyforge.tenancy``), not imported
by ``import pyforge``. No extra dependency.

Two independent strategies, usable separately or together:

- **Shared database, tenant_id column** — mix :class:`TenantScopedMixin`
  into a `Model`; every read/write through it is scoped to the current
  tenant automatically.
- **Database per tenant** — :class:`TenantDatabaseManager` routes
  ``session_scope()`` to a distinct connection per tenant.

Both read the current tenant from the same place: :func:`current_tenant_id`
(or the ``_or_none`` variant), set by :func:`tenant_scope` or
:class:`TenantResolutionMiddleware`.

    from pyforge.tenancy import TenantScopedMixin, TenantResolutionMiddleware, subdomain_tenant_resolver
"""

from .context import current_tenant_id, current_tenant_id_or_none, set_current_tenant, tenant_scope
from .database import TenantDatabaseManager
from .middleware import (
    TenantResolutionMiddleware,
    header_tenant_resolver,
    subdomain_tenant_resolver,
)
from .model import TenantScopedMixin

__all__ = [
    "TenantDatabaseManager",
    "TenantResolutionMiddleware",
    "TenantScopedMixin",
    "current_tenant_id",
    "current_tenant_id_or_none",
    "header_tenant_resolver",
    "set_current_tenant",
    "subdomain_tenant_resolver",
    "tenant_scope",
]
