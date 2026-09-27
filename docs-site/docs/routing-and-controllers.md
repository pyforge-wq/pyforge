# Routing & Controllers

## Plain functions

Registered exactly as FastAPI would — no wrapping, full native
parameter/dependency inference:

```python
from pyforge import Router

router = Router()

router.get("/health", lambda: {"status": "ok"})

async def show_user(id: int) -> dict:
    return {"id": id}

router.get("/users/{id}", show_user)
```

## Controllers

Controllers are plain classes — no base class required:

```python
class UserController:
    async def index(self) -> list[dict]:
        return [{"id": 1}]

    async def show(self, id: int) -> dict:
        return {"id": id}
```

```python
router.get("/users", UserController.index)
router.post("/users", UserController.store)
router.get("/users/{id}", UserController.show, name="users.show")
```

An **unbound method reference** like `UserController.show` is detected
automatically (by inspecting `__qualname__` and the first parameter being
`self`) and wrapped so a fresh controller instance is resolved from the
[dependency injection container](dependency-injection-and-config.md) on
every request, while the wrapped endpoint's signature is rewritten to drop
`self`. FastAPI never sees `self` — path params, request bodies, and
`Depends()` on the *rest* of the method signature all work exactly as they
would on a plain function.

```python
class UserController:
    def __init__(self, users: UserRepository) -> None:  # autowired
        self.users = users

    async def show(self, id: int) -> dict:
        return self.users.find(id)
```

!!! warning "Controllers must be defined at module level"
    `Router` only recognizes a handler as a controller action when its
    `__qualname__` doesn't contain `<locals>` — i.e. the class is defined at
    the top of a module, not inside a function body. Defining a controller
    class inside a test function (or any other function) will silently fail
    route resolution. See [Troubleshooting](troubleshooting.md#a-controller-route-silently-doesnt-work)
    for the exact symptom and fix.

## Route groups

`router.group(...)` is a context manager: routes registered on the yielded
`Router` are mounted onto the parent when the `with` block exits, with a
path prefix, middleware-derived dependencies, and tags applied.

```python
with router.group(prefix="/api/v1", middleware=["auth"], name="v1") as group:
    group.get("/me", ProfileController.show, name="me")
    # -> registered as "v1.me", path "/api/v1/me"
```

## Named routes and URL generation

```python
router.get("/users/{id}", UserController.show, name="users.show")
router.url("users.show", id=42)   # -> "/users/42"
```

A `name=` prefix on a group namespaces every route registered inside it
(`name="v1"` + `name="me"` → `"v1.me"`).

## What's not built yet

Route-model binding (resolving `id: int` straight to a `User` instance
automatically) isn't implemented — a controller calls
`User.find_or_fail(id)` itself:

```python
class UserController:
    async def show(self, id: int) -> dict:
        user = User.find_or_fail(id)   # raises ModelNotFoundError -> 404
        return {"id": user.id, "name": user.name}
```

## Plain FastAPI, always available

Nothing about PyForge hides FastAPI. `app.fastapi` is a real
`fastapi.FastAPI` instance, not a lookalike:

```python
from pyforge import PyForge

app = PyForge()

@app.get("/hello")
async def hello():
    return {"message": "Hello"}

app.fastapi.add_middleware(SomeStarletteMiddleware)
app.fastapi.add_exception_handler(ValueError, my_handler)
```

Any FastAPI middleware, dependency, sub-router, or response class works
unmodified. `app` itself is ASGI-callable — `uvicorn main:app` works without
reaching into `.fastapi` at all.

## Middleware

See the dedicated [Middleware](middleware.md) guide for named,
route-scoped middleware (`middleware=["auth"]` above) versus global
ASGI-level middleware (`app.use_middleware(...)`).
