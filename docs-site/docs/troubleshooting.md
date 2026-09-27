# Troubleshooting

The gotchas on this page account for the vast majority of "why doesn't this
work" moments with PyForge. If you hit something not listed here, please
[open an issue](https://github.com/pyforge-framework/pyforge/issues) — this
page is meant to grow.

## A controller route silently doesn't work

**Symptom:** a route registered with `router.get("/x", SomeController.method)`
either 422s with a confusing `self` parameter, raises a `TypeError` about a
missing argument, or otherwise behaves as if `SomeController.method` were a
plain function rather than a controller action.

**Cause:** the controller class was defined **inside a function** (most
commonly a test function) rather than at module level. `Router` only
recognizes a handler as a controller action when its `__qualname__` doesn't
contain `<locals>` — a class defined inside a function has exactly that in
its qualname, so the detection silently falls through and the raw unbound
method gets registered as if it were a plain function, `self` and all.

**Fix:** move the controller class to module scope.

```python
# Breaks — class is local to the test function:
def test_something():
    class MyController:
        async def index(self) -> dict: ...
    router.get("/x", MyController.index)

# Works:
class MyController:
    async def index(self) -> dict: ...

def test_something():
    router.get("/x", MyController.index)
```

## `RuntimeError: No default Auth configured`

**Cause:** a bare `@role(...)` or `@permission(...)` decorator ran before
`set_default_auth(auth)` was called. These decorators resolve their
dependency at class-*definition* time (i.e. at import time), not per
request — so if the module defining the decorated controller is imported
before your service provider's `register()` (which calls
`set_default_auth(...)`) has run, this is what you get.

**Fix:** make sure providers are registered before `routes/` is imported.
The generated project's `main.py` already does this in the right order —
double-check you haven't imported a controller module earlier than that
(e.g. from another module that's imported first). Alternatively, pass
`get_user=` explicitly to the decorator instead of relying on the default:

```python
@role("admin", get_user=auth.required)
```

Or use [`current_user`](authentication.md#current_user-the-import-order-safe-way)
instead of the decorators, which resolves the default `Auth` at request
time and sidesteps the ordering issue entirely.

## Login works, but the session cookie never comes back

**Cause:** `Auth.session_login` defaults to `secure=True` — the cookie is
only ever sent back over HTTPS. Testing locally over plain `http://`
(including with `httpx`'s `TestClient`, which enforces the same rule as a
real browser) means the cookie gets set but never sent back on the next
request, so `session_required` 401s and it looks like "login doesn't work."

**Fix:** pass `secure=False` explicitly for local development/tests:

```python
auth.session_login(response, user, secure=False)
```

Never do this in production — see [Security](security.md#session-cookies).

## A job's side effects don't show up in my test

**Cause:** a `Job`'s attributes are captured **by value** at dispatch time
(it's pickled for the Redis driver, and even the sync driver's contract
matches this). If your job appends to a list held as an *instance*
attribute and your test inspects that same instance afterward, you're
looking at a different object than the one that actually ran — pickling (or
even just the by-value dispatch contract) means the job that executed isn't
the same Python object your test still has a reference to.

**Fix:** record results somewhere both sides can see — a database row, or a
plain **module-level** list/variable (module-level state survives because
unpickling reuses the already-imported module's namespace):

```python
_LOG: list[str] = []   # module-level, not an instance attribute

class SendWelcomeEmail(Job):
    def handle(self) -> None:
        _LOG.append("sent")
```

Or better: use [`fake_queue()`](testing.md#pyforgetesting-fakes-and-assertion-helpers)
and assert the job was pushed, without needing to inspect its side effects
at all.

## `RuntimeError: No active database session`

**Cause:** a `Model` method ran outside a `session_scope()` — either the
code isn't running inside an HTTP request (where PyForge opens one
automatically) or it's a script/test that never opened one manually.

**Fix:**

```python
from pyforge.database import session_scope

with session_scope():
    User.create(name="Ada")
```

## `RuntimeError: No database is configured`

**Cause:** the project has no `config/database.py`. `pyforge new` generates
one by default — if you deleted it or moved it, database features (`Model`,
migrations, `db:seed`) won't work until it's restored.

## `KeyError: Unknown middleware 'x'. Register it first with app.middleware.register(...)`

**Cause:** `router.group(middleware=["x"])` referenced a name that was never
registered.

**Fix:** register it — typically in a service provider's `boot()` (register
happens too early; the app/container isn't fully wired until boot):

```python
class AppServiceProvider(ServiceProvider):
    def boot(self) -> None:
        self.app.middleware.register("x", your_dependency_function)
```

See [Middleware](middleware.md).

## `sqlite3.OperationalError: no such table` / similar from another database

**Cause:** the migration for that table was never applied.

**Fix:**

```bash
pyforge migrate
pyforge migrate:status   # to check what's actually applied
```

## A `FormRequest` parameter isn't being validated

**Cause:** auto-injection only kicks in when the parameter has **no
explicit default**. If you wrote `request: CreateUserRequest = None` or
already supplied `Depends(...)` yourself, PyForge leaves it alone —
whichever you wrote wins.

**Fix:** declare it with no default at all:

```python
async def store(self, request: CreateUserRequest) -> dict: ...   # auto-injected
```

## `pip install .` fails on a generated project with a hatchling "Unable to determine which files to ship" error

**Cause:** this was a real bug in `pyforge-framework` versions before
`0.7.0` — the generated `pyproject.toml` had no
`[tool.hatch.build.targets.wheel]` configuration, and a generated project's
flat layout (`main.py`, `routes/`, `config/` at the top level, not a
`<project_name>/` package directory) confuses hatchling's default file
selection.

**Fix:** upgrade to `pyforge-framework>=0.7.0` and regenerate the project
(or add `bypass-selection = true` under
`[tool.hatch.build.targets.wheel]` in the existing project's
`pyproject.toml` by hand).

## Redis cache `.flush()` wiped something unrelated

**Cause:** `RedisCacheDriver.flush()` runs `FLUSHDB` — every key in that
Redis **database index**, not just PyForge's own keys.

**Fix:** point the cache at a dedicated Redis DB index, not one shared with
anything else (including the queue driver, if you're also using
`pyforge.queue`'s Redis driver).

## Still stuck?

Check [09-roadmap.md](https://github.com/pyforge-framework/pyforge/blob/main/docs/architecture/09-roadmap.md)
for whether the thing you're trying to do is actually built yet — several
features that sound like they should exist (route-model binding, job
timeouts, an admin UI, autogenerate-by-default migrations) are explicitly
not implemented, by design, for now. If it's not there, it's either
deliberately deferred or worth a feature request.
