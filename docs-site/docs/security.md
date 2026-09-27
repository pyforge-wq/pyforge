# Security

PyForge's rule for security-sensitive code: **never reinvent cryptography.**
Every item below wraps an established library rather than implementing a
crypto primitive itself. This page is the task-oriented version; the
in-repo [architecture doc](https://github.com/pyforge-framework/pyforge/blob/main/docs/architecture/10-security.md)
walks the same checklist in full audit-report detail, including what was
found and fixed during the Phase 7 review.

## Passwords

```python
from pyforge.auth import hash_password, verify_password

hashed = hash_password(raw_password)      # bcrypt
verify_password(raw_password, hashed)     # True/False
```

Never store or compare a plaintext password — `Auth.attempt(...)` always
goes through `verify_password` against the stored hash.

## JWTs

`pyforge.auth` always decodes with an explicit, pinned algorithm list
(`jwt.decode(token, secret, algorithms=[algorithm])`) — this is what
prevents the classic `"alg": "none"`/algorithm-confusion JWT vulnerability.
Every token carries a `purpose` claim checked on every use, so a token
issued for one purpose can never be replayed as another. Rotate
`JWT_SECRET` in production through your deployment platform's secret
manager — never commit it. `pyforge new` already generates a real random
one per project.

## CORS

Not a PyForge-specific feature — use Starlette's `CORSMiddleware` directly:

```python
from starlette.middleware.cors import CORSMiddleware

app.use_middleware(CORSMiddleware, allow_origins=["https://example.com"], allow_credentials=True)
```

## Rate limiting

```python
from pyforge.security import rate_limit

class LoginController:
    @rate_limit("5/minute")
    async def attempt(self, request: LoginRequest) -> dict: ...
```

A fixed-window counter in the configured cache (`key_func=` to customize the
bucket key, default is client IP; `cache=` to use something other than
`default_cache()`). Not exact at window boundaries, and single-process
unless the Redis cache driver is used — see the Redis note below.

## Secure headers

```python
from pyforge.security import SecurityHeadersMiddleware

app.use_middleware(SecurityHeadersMiddleware)
```

Sets `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, and `Strict-Transport-Security` (on HTTPS requests
only) — never overrides a header your own code already set. No default
`Content-Security-Policy` (there's no sane one-size-fits-all value); pass
`content_security_policy=` if you want one.

## Session cookies

```python
auth.session_login(response, user)   # secure=True by default
```

Always `httponly` (no JS access) and `samesite="lax"`. `secure=True` by
default — pass `secure=False` explicitly only for local `http://localhost`
development. See [Authentication](authentication.md#cookie-based-sessions).

## Input validation

Every request body a controller declares a typed parameter for — a
`FormRequest` or a native Pydantic model — is validated before the handler
runs. There's no way to accept an untyped, unvalidated body through
PyForge's routing by omission. See [Validation & API Resources](validation-and-api.md).

## SQL injection

Every query PyForge itself builds goes through SQLAlchemy's parameterized
query construction. Table/column *names* referenced by the ORM or migration
DSL always come from your own code, never from request data. The one
escape hatch, `QueryBuilder.having(...)`, accepts a raw SQLAlchemy
expression — building one from unsanitized string concatenation is on you,
same as with raw SQLAlchemy directly.

## Mass assignment

There is **no** `$fillable`/`$guarded`-style allowlist on
`Model.create(**attributes)`/`.update(**attributes)` — every keyword you
pass is set directly.

```python
# Dangerous IF `rules` ever includes a framework-managed field like `role` or `tenant_id`:
Post.create(**request.validated())
```

Until an allowlist mechanism exists, construct security-sensitive
`create()`/`update()` calls with explicit, individually-named keyword
arguments rather than spreading a whole validated dict:

```python
Post.create(title=request.validated()["title"], author_id=current_user.id)
```

The one place this is already closed for you: [multi-tenancy](multi-tenancy.md)'s
`TenantScopedMixin.create()` force-overwrites any caller-supplied
`tenant_id`, so a spoofed value in request data can't leak a write across
tenants.

## Redis and the `pickle` trust boundary

`RedisCacheDriver` and `RedisQueueDriver` use `pickle` to store arbitrary
Python values — standard practice for an app's own private cache/queue. But
`pickle.loads` on data from a Redis instance you don't fully control is a
remote-code-execution risk, not just a data-integrity one. **Point
`REDIS_URL` at a private instance only your own application writes to.**

## Secret management

JWT secrets, database credentials, and mail/S3 credentials all come from
`config(...)` → `env(...)` → `.env`/real environment variables — never
hardcoded, and `.env` is `.gitignore`d from project creation. PyForge
doesn't ship its own secret-storage or rotation mechanism — use your
deployment platform's.

## File uploads

Not built as a validation-rule layer. Use FastAPI's `UploadFile` directly
and validate size/content type yourself before calling `Storage.put(...)` —
see [Storage & Cache](storage-and-cache.md#storage-pyforgestorage).

## Reporting a vulnerability

See [SECURITY.md](https://github.com/pyforge-framework/pyforge/blob/main/SECURITY.md)
for how to report privately rather than as a public GitHub issue.
