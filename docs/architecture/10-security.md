# Security

A first-class concern per the original spec's own list — this document
walks that exact list and states, plainly, what PyForge does and doesn't do
for each, including gaps found and fixed (or just documented) during a
manual security review of Phases 1-7. "Never reinvent cryptography" is the
one rule every item below follows: PyForge always wraps an established
library rather than implementing crypto primitives itself.

## Password hashing

`pyforge.auth.hash_password`/`verify_password` — bcrypt via the `bcrypt`
package, nothing hand-rolled. `Auth.attempt(...)` always compares against
the stored hash, never a plaintext password.

## JWT security

`pyforge.auth.jwt` uses PyJWT, and always calls `jwt.decode(token, secret,
algorithms=[algorithm])` with an explicit, pinned algorithm list — this is
what prevents the classic `"alg": "none"` / algorithm-confusion JWT
vulnerability class (PyJWT rejects a token whose header claims an algorithm
outside that list, rather than trusting whatever the token itself says).
Every token (access, refresh, session, and the email-verification/
password-reset signed tokens) carries a `purpose` claim and is checked
against it, so a token issued for one purpose can never be replayed as
another (a refresh token can't be used as an access token, etc. — see
`tests/test_auth.py`).

**Secrets**: `JWT_SECRET` comes from `config("auth.jwt.secret")` / the
`.env` file — `pyforge new` generates a real random secret
(`secrets.token_urlsafe(32)`) into `.env` for every new project rather than
shipping a static placeholder; `.env.example` (which *is* meant to be
committed) keeps a `change-me` placeholder instead. Rotate `JWT_SECRET` in
production the same way you'd rotate any other secret — through your
deployment's secret manager / environment configuration, never committed.

## CORS

Not a PyForge-specific feature — use Starlette's own `CORSMiddleware`
directly, since PyForge never hides FastAPI:

```python
from starlette.middleware.cors import CORSMiddleware

app.use_middleware(CORSMiddleware, allow_origins=["https://example.com"], allow_credentials=True)
```

## Rate limiting

`pyforge.security.rate_limit("60/minute")` — see
[03-public-api-design.md](03-public-api-design.md). A fixed-window counter
in the configured cache; not exact at window boundaries, and single-process
unless the Redis cache driver is used (see the pickle/Redis note below for
what that implies about trust).

## Input validation

`FormRequest` (pipe-separated string rules) and native Pydantic models both work as
controller parameter types — see
[03-public-api-design.md](03-public-api-design.md). Every request body a
controller declares a typed parameter for is validated before the handler
runs; an untyped `**kwargs`-style body is not something PyForge's routing
supports, so there's no way to accidentally skip validation by omission.

## SQL injection protection

Every query PyForge itself builds — `QueryBuilder`, `Model`, the
`validate()` rule engine's `unique:table,column` check — goes through
SQLAlchemy's parameterized query construction (`.where(column == value)`
etc.); table/column *names* referenced by the ORM or the Schema migration
DSL always come from developer-authored code (model/migration definitions),
never from request data, so there's no path from user input to a
dynamically-built SQL string. `QueryBuilder.having(...)` accepts a raw
SQLAlchemy expression as an escape hatch — building one of those from
unsanitized string concatenation is on the developer, the same as it would
be with raw SQLAlchemy directly.

## Secure headers

`pyforge.security.SecurityHeadersMiddleware` — `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and
`Strict-Transport-Security` on HTTPS requests. No default
`Content-Security-Policy` (there's no sane one-size-fits-all value); pass
`content_security_policy=` if you want one. Never overrides a header your
own code already set.

## File upload restrictions

**Not built.** FastAPI's native `UploadFile` (size via `Content-Length`,
`content_type` inspection) is directly usable and is the documented way to
handle uploads today; PyForge doesn't add a validation-rule layer on top of
it (no `"file|max:2048|mimes:jpg,png"`-style rule in `pyforge.validation`
yet). If you accept uploads, validate size and content type yourself before
calling `Storage.put(...)` — `LocalStorageDriver`/`S3StorageDriver` write
whatever bytes they're given, with no restriction of their own beyond the
local driver's path-traversal check.

## Authentication protection

Every `Auth`/`ApiTokenAuth` guard (`required`, `session_required`, API
tokens) raises `401` on a missing/invalid/expired/wrong-purpose token —
verified in `tests/test_auth.py` for every combination, including that a
refresh token can't authenticate a normal request and vice versa.

**Session cookies** (`Auth.session_login`) default to `secure=True` — the
cookie is only ever sent back over HTTPS, matching production best
practice. Pass `secure=False` explicitly for local `http://localhost`
development (a real browser — and `httpx`'s `TestClient`, which enforces
the same rule — silently drops a secure cookie sent over plain HTTP; this
is a deliberate browser behavior PyForge relies on rather than works
around). Always `httponly` (no JS access) and `samesite="lax"`.

## Authorization

`Policy` + `authorize(...)`, and the `@role`/`@permission` decorators — see
[03-public-api-design.md](03-public-api-design.md). Both fail closed:
`authorize(...)` raises `403` unless the policy method explicitly returns
truthy, and the decorators 403 unless the resolved user matches.

## Tenant isolation

`pyforge.tenancy.TenantScopedMixin.create()` **overwrites** any
caller-supplied `tenant_id` with the current tenant rather than only
filling it in when absent — found during this review as the one place a
mass-assignment bug (see below) could have broken tenant isolation
specifically, since a `tenant_id` slipping through from request data would
otherwise let one tenant write into another's rows. `query()`/`all()`/
`find()`/`where()` are all scoped through the same `query()` override, with
no per-call opt-out. See `tests/test_tenancy.py`, including a regression
test for exactly this (`test_create_overrides_a_caller_supplied_tenant_id`).

## Secret management

JWT secrets, database credentials, mail/S3 credentials all come from
`config(...)` → `env(...)` → `.env` / real environment variables — never
hardcoded in source, and `.env` is `.gitignore`d by the generated project
template from the start. PyForge doesn't ship its own secret-storage or
-rotation mechanism; use your deployment platform's.

## Known gaps found during this review (not fixed, documented instead)

- **Mass assignment**: `Model.create(**attributes)`/`.update(**attributes)`
  have no `$fillable`/`$guarded`-style allowlist — every keyword
  argument is accepted and set directly. A controller that does something
  like `Post.create(**request.validated())` is safe *only* insofar as the
  `FormRequest`'s own `rules` dict controls which fields exist in
  `validated()` — if a `rules` dict is ever widened to include a
  framework-managed field (an `id`, a `role`, a `tenant_id` on a model
  *without* `TenantScopedMixin`'s override), that field becomes
  mass-assignable. There's no allowlist mechanism to opt into yet; until
  there is, construct `create()`/`update()` calls with explicit,
  individually-named keyword arguments for anything security-sensitive
  rather than spreading a whole validated dict, and see
  [06-database-architecture.md](06-database-architecture.md) for where a
  `__fillable__`/`__guarded__` mechanism would go if a real need for one
  shows up (not built speculatively, matching this project's own rule
  against premature abstraction).
- **Pickle deserialization trust boundary**: `RedisCacheDriver` and
  `RedisQueueDriver` use `pickle.dumps`/`pickle.loads` to store arbitrary
  Python values. This is standard practice for an app's *own*, private
  cache/queue backend (the same default Django's cache framework and
  Celery historically used) — but `pickle.loads` on data from a Redis
  instance you don't fully control (shared with untrusted tenants, exposed
  to the internet, writable by anything you don't trust) is a remote-code-
  execution risk, not just a data-integrity one. Point `REDIS_URL` at a
  private instance only your own application writes to.
