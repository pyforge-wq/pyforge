# Authentication

`pyforge.auth` is an **optional module** — not imported by `import pyforge`.
Install the extra and import it explicitly:

```bash
pip install "pyforge-framework[auth]"
```

```python
from pyforge.auth import Auth, hash_password, current_user
```

Everything in this module is built on one primitive: a signed, expiring JWT
carrying a `purpose` claim (`access`, `refresh`, `session`, or a custom
purpose for signed tokens). A token issued for one purpose can never be
replayed as another — a refresh token can't authenticate a normal request,
a session cookie can't be used as a bearer token.

## Set it up once

Typically in a service provider, so it runs before `routes/` is imported
(see the import-order note below):

```python
from pyforge.auth import Auth, set_default_auth
from app.models.user import User

auth = Auth(User, secret=config("auth.jwt.secret"))
set_default_auth(auth)
```

`Auth(user_model, *, secret, algorithm="HS256", access_ttl_minutes=60, refresh_ttl_minutes=60*24*14, email_field="email", password_field="password_hash", login_url="auth/login")`
— every keyword has a sensible default; override `email_field`/
`password_field` if your user model names them differently.

## Password hashing

```python
from pyforge.auth import hash_password, verify_password

user = User.create(email="ada@example.com", password_hash=hash_password("s3cret"))
verify_password("s3cret", user.password_hash)   # True
```

bcrypt underneath — nothing hand-rolled. `Auth.attempt(...)` always compares
against the stored hash.

## Bearer-token login (access + refresh tokens)

```python
class AuthController:
    def __init__(self, auth: Auth) -> None:   # autowired via the container
        self.auth = auth

    async def login(self, request: LoginRequest) -> dict:
        user = self.auth.attempt(request.email, request.password)
        if user is None:
            raise HTTPException(401, "Invalid credentials")
        return self.auth.login(user)   # {"access_token", "refresh_token", "token_type"}

    async def refresh(self, refresh_token: str) -> dict:
        return self.auth.refresh(refresh_token)   # {"access_token", "token_type"}
```

Guard a route with the bearer-token dependency:

```python
class ProfileController:
    async def me(self, user: Any = Depends(auth.required)) -> dict:
        return {"id": user.id, "email": user.email}
```

`auth.optional` is the same thing but returns `None` instead of raising
`401` when there's no valid token — for endpoints that behave differently
for logged-in vs. anonymous users without requiring login.

### `current_user` — the import-order-safe way

```python
from pyforge.auth import current_user

class ProfileController:
    async def me(self, user: Any = Depends(current_user)) -> dict:
        return {"id": user.id}
```

`Depends(auth.required)` needs a specific, already-built `Auth` instance in
scope. `Depends(current_user)` instead looks up whichever `Auth` was
registered via `set_default_auth(...)` **at request time** — use it in any
controller that has no other reason to hold a specific `Auth` instance, so
import order relative to `set_default_auth(...)` never matters.

## Cookie-based sessions

```python
class SessionController:
    async def login(self, response: Response, request: LoginRequest) -> dict:
        user = auth.attempt(request.email, request.password)
        if user is None:
            raise HTTPException(401, "Invalid credentials")
        auth.session_login(response, user)   # secure=True by default
        return {"ok": True}

    async def logout(self, response: Response) -> dict:
        auth.session_logout(response)
        return {"ok": True}

class ProfileController:
    async def me(self, user: Any = Depends(auth.session_required)) -> dict:
        return {"id": user.id}
```

`session_login(response, user, *, secure=True)` sets an `httponly`,
`samesite="lax"` cookie. **`secure=True` is the default** — the cookie is
only ever sent back over HTTPS. Pass `secure=False` explicitly for local
`http://localhost` development; a real browser (and `httpx`'s `TestClient`,
which enforces the same rule) silently drops a secure cookie sent over
plain HTTP, so leaving the default on in a local dev test looks like "login
doesn't work" if you don't know this. See
[Troubleshooting](troubleshooting.md#login-works-but-the-session-cookie-never-comes-back)
for the exact symptom.

## Signed tokens for email verification / password reset

The same primitive, a different `purpose`:

```python
token = auth.make_signed_token(user.id, purpose="password_reset", ttl_minutes=30)
# send `token` in an email yourself, via pyforge.mail — Auth doesn't send email

user = auth.verify_signed_token(token, purpose="password_reset")
if user is None:
    raise HTTPException(400, "Invalid or expired token")
```

A token verified against the wrong `purpose` returns `None`, not the user —
a `password_reset` token can't be replayed to verify an email address.

## API tokens (personal access tokens)

For machine clients that shouldn't carry short-lived JWTs — Sanctum-style
plaintext-once tokens, hashed at rest:

```python
from pyforge.auth import ApiTokenAuth

class PersonalAccessToken(Model):
    __tablename__ = "personal_access_tokens"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)

api_tokens = ApiTokenAuth(PersonalAccessToken, User)

class TokenController:
    async def store(self, user: Any = Depends(auth.required)) -> dict:
        return {"token": api_tokens.issue(user)}   # shown once, never recoverable again

class ProfileController:
    async def me(self, user: Any = Depends(api_tokens.required)) -> dict:
        return {"id": user.id}
```

`ApiTokenAuth` deliberately doesn't force a fixed token-table schema —
it only needs to know two field names (`token_field`, `user_id_field`,
both overridable), so your table can carry a name, `last_used_at`, an
expiry, or whatever else your app needs.

## Guarding with roles and permissions

See [Authorization](authorization.md) for `@role(...)`, `@permission(...)`,
and `Policy`/`authorize(...)` — all built on top of the `Auth` dependencies
above.

## What's not built

OAuth2 as a full provider (authorization-code flow, client registration,
scopes) or third-party login (Google/GitHub/...) isn't implemented — only
`OAuth2PasswordBearer`-compatible Swagger UI integration for the JWT bearer
flow. A real OAuth2 server/client is a substantially larger, separately
scoped feature.
