# Authorization

Requires `pyforge.auth` (`pip install "pyforge-framework[auth]"`) — see
[Authentication](authentication.md) for setting up `Auth` and
`set_default_auth(...)` first.

## `@role` and `@permission` decorators

```python
from pyforge.auth import role, permission

class AdminController:
    @role("admin")
    async def stats(self) -> dict:
        return {"secret": True}

class UserController:
    @permission("users.create")
    async def store(self, request: CreateUserRequest) -> dict:
        ...
```

- `@role(name)` — 403s unless the resolved user's `.role` attribute equals
  `name`.
- `@permission(name)` — 403s unless `user.has_permission(name)` (a method
  your user model implements) returns truthy:

```python
class User(Model):
    role: Mapped[str] = mapped_column(String(50), default="user")

    def has_permission(self, name: str) -> bool:
        return self.role == "admin"   # or a real permissions table
```

Both decorators resolve the current user through the default `Auth`'s
`.required` (bearer-token) dependency by default. Pass `get_user=` for a
different one — e.g. cookie-session auth instead:

```python
@role("admin", get_user=auth.session_required)
```

!!! warning "Import-order gotcha"
    `@role(...)`/`@permission(...)` resolve their dependency at class
    *definition* time (when the module is imported), not per-request — so
    `set_default_auth(...)` must run **before** any module using the bare
    decorator form is imported. The generated project's `main.py` registers
    providers before importing `routes/` for exactly this reason. If you see
    `RuntimeError: No default Auth configured`, this is almost always why —
    see [Troubleshooting](troubleshooting.md#runtimeerror-no-default-auth-configured).

## Policies

For per-object authorization checks (not just role/permission, but "does
*this* user own *this* record"):

```python
from pyforge.auth import Policy, authorize

class PostPolicy(Policy):
    def update(self, user, post) -> bool:
        return user.id == post.author_id
```

```python
class PostController:
    async def update(self, id: int, user: Any = Depends(current_user)) -> dict:
        post = Post.find_or_fail(id)
        authorize(PostPolicy(), "update", user, post)   # raises 403 if falsy
        ...
```

`authorize(policy, action, user, *args, **kwargs)` calls
`policy.<action>(user, *args, **kwargs)` and raises
`HTTPException(403, "This action is unauthorized.")` if it returns a falsy
value. Policies are plain classes — no registration step, no mapping a
model to its policy automatically; you call `authorize(...)` explicitly
where it matters.

## Generate one

```bash
pyforge make:policy Post
```

## Both fail closed

`authorize(...)` raises unless the policy method explicitly returns
truthy; the decorators 403 unless the resolved user actually matches. There
is no default-allow path in either mechanism.
