# Multi-tenancy

`pyforge.tenancy` is optional (no extra dependency needed) and offers two
independent strategies — pick one, or combine them.

## Strategy 1: shared database, `tenant_id` column

```python
from pyforge.tenancy import TenantScopedMixin, TenantResolutionMiddleware, subdomain_tenant_resolver

class Post(TenantScopedMixin, Model):
    __tablename__ = "posts"
    title: Mapped[str] = mapped_column(String(255))

app.use_middleware(TenantResolutionMiddleware, resolver=subdomain_tenant_resolver)
```

```python
Post.all()               # scoped to the current request's tenant automatically
Post.create(title="Hi")  # tenant_id stamped in automatically
```

`TenantScopedMixin` overrides `Model.query()` and `.create()` — every other
read method (`.all()`, `.find()`, `.where()`) goes through `query()`, so
they're scoped for free. With a current tenant set, every read/write through
it is confined to that tenant; with none set, it's unscoped.

!!! danger "`.create()` always wins over caller-supplied data"
    `TenantScopedMixin.create()` **overwrites** any caller-supplied
    `tenant_id` rather than only filling it in when absent. This closes a
    real mass-assignment risk: if a controller ever does something like
    `Post.create(**request.validated())` and a `tenant_id` field slips
    through from request data, the override prevents it from writing into
    another tenant's rows. There is deliberately no per-call escape hatch to
    see or write another tenant's rows through this mixin.

### Resolving the current tenant

```python
from pyforge.tenancy import tenant_scope, header_tenant_resolver

# from a middleware/resolver:
app.use_middleware(TenantResolutionMiddleware, resolver=subdomain_tenant_resolver)
# or:
app.use_middleware(TenantResolutionMiddleware, resolver=header_tenant_resolver("X-Tenant-ID"))

# manually, e.g. in a script or test:
with tenant_scope("acme"):
    Post.create(title="Only visible to acme")
```

Both strategies below read the current tenant from the same place —
`current_tenant_id()` / `current_tenant_id_or_none()` — set by
`tenant_scope(...)` or `TenantResolutionMiddleware`. Write your own resolver
function if `subdomain_tenant_resolver`/`header_tenant_resolver(...)` don't
match how your app identifies a tenant (a JWT claim, a path segment, ...).

## Strategy 2: database per tenant

```python
from pyforge.tenancy import TenantDatabaseManager, set_current_database

def connection_for_tenant(tenant_id: str) -> dict:
    return {"driver": "mysql", "database": f"tenant_{tenant_id}", "host": "...", ...}

set_current_database(TenantDatabaseManager(connection_for_tenant=connection_for_tenant))
```

`TenantDatabaseManager` routes `session_scope()` to a distinct, lazily-built
`DatabaseManager` per tenant — a drop-in replacement for
`set_current_database(...)`, so `Model` and every other database-touching
call works completely unmodified. It plugs into core via
`DatabaseManagerLike`, a `typing.Protocol` — see [Extending PyForge](packages.md)
for what that pattern means if you're building your own package.

## Which strategy should I use?

| | Shared DB (`TenantScopedMixin`) | DB per tenant (`TenantDatabaseManager`) |
|---|---|---|
| Isolation | Row-level, enforced by every query going through `query()` | Full physical isolation — a bug can't leak across tenants at the SQL level |
| Operational cost | One database to manage | N databases, N connections, N migration runs |
| Good for | Most SaaS apps — simpler to run and query across tenants | Regulatory isolation requirements, very large tenants, heavy per-tenant customization |

Nothing stops you from combining them (some tables shared and scoped, others
routed per-tenant) — both read from the same `current_tenant_id()`.
