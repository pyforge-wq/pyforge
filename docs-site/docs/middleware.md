# Middleware

PyForge has two distinct kinds of middleware — don't confuse them, they
solve different problems.

## Named, route-scoped middleware

A FastAPI *dependency* registered under a short name, used to guard specific
routes or route groups — auth checks, tenant resolution, rate limiting. This
is the "attach middleware to this route group" pattern familiar from
full-stack web frameworks.

Generate one:

```bash
pyforge make:middleware Auth
```

```python
# app/middleware/auth.py
from fastapi import Request, HTTPException

async def auth(request: Request) -> None:
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(401, "Missing token")
```

Register it — typically in a service provider's `boot()`:

```python
class AppServiceProvider(ServiceProvider):
    def boot(self) -> None:
        self.app.middleware.register("auth", auth)
```

Use it on a route group by name:

```python
with router.group(prefix="/admin", middleware=["auth"]) as group:
    group.get("/stats", AdminController.stats)
```

Under the hood, `app.middleware` is a `MiddlewareRegistry` mapping names to
dependency callables; `router.group(middleware=[...])` resolves each name to
`Depends(fn)` and attaches it to every route in the group. An unregistered
name raises immediately (`KeyError: Unknown middleware 'x'. Register it
first with app.middleware.register(...)`) rather than silently doing
nothing.

## Global, ASGI-level middleware

For anything that isn't a per-route guard — CORS, GZip compression, security
headers, request logging — use the standard FastAPI/Starlette API directly,
exposed as `app.use_middleware(...)`:

```python
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from pyforge.security import SecurityHeadersMiddleware

app.use_middleware(CORSMiddleware, allow_origins=["https://example.com"], allow_credentials=True)
app.use_middleware(GZipMiddleware, minimum_size=1000)
app.use_middleware(SecurityHeadersMiddleware)
```

`use_middleware` is a thin passthrough to `FastAPI.add_middleware` — nothing
PyForge-specific about it, and any third-party Starlette middleware works
unmodified.

## Which one do I want?

| | Named middleware (`app.middleware.register`) | Global middleware (`app.use_middleware`) |
|---|---|---|
| Runs on | Only the routes/groups it's attached to | Every request |
| Shape | An async function taking `Request` (a FastAPI dependency) | A Starlette `BaseHTTPMiddleware`/ASGI middleware class |
| Typical use | Auth guards, `@role`/`@permission`-style checks, tenant resolution | CORS, security headers, compression, logging |
| Attach via | `router.group(middleware=["name"])` | `app.use_middleware(Class, **options)` |

See [Authentication](authentication.md) and [Authorization](authorization.md)
for the auth-specific guards (`auth.required`, `@role`, `@permission`) that
build on this same mechanism, and [Multi-tenancy](multi-tenancy.md) for
`TenantResolutionMiddleware`, which is a global middleware.
