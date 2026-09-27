# Testing Architecture

## Testing the framework itself

`tests/` in this repository tests PyForge's own public API in isolation —
no generated project involved:

- `test_container.py` — binding, singleton vs. transient, autowiring,
  failure modes (`BindingResolutionError`).
- `test_config.py` — loading namespaced `config/*.py` files, dot-notation
  get/set, `env()` casting.
- `test_router.py` — plain-function routes, controller-action wrapping
  (including that a controller is instantiated fresh per request), named
  routes, route groups (prefix + name namespacing), and middleware rejecting
  requests — each verified against a real `fastapi.testclient.TestClient`,
  never mocked.
- `test_application.py` — config/`.env` loading from `base_path`, mounting a
  `Router`, `PyForge` being ASGI-callable directly, the two-phase
  `ServiceProvider` lifecycle (`register()` immediate, `boot()` on startup),
  and that the container can resolve the running `PyForge` instance itself.

Run with:

```bash
pip install -e ".[dev]"
pytest
```

`tests/conftest.py` inserts `src/` onto `sys.path` so the suite runs against
the working tree without requiring an editable install first — convenient
for contributors, though CI (see [.github/workflows/ci.yml](../../.github/workflows/ci.yml))
still exercises the real installed package.

## Testing a PyForge application

Every generated project (`pyforge new myapp`) ships a real, passing test —
`tests/test_welcome.py` — demonstrating the pattern:

```python
from fastapi.testclient import TestClient
from main import app

def test_health() -> None:
    client = TestClient(app.fastapi)
    response = client.get("/api/health")
    assert response.status_code == 200
```

Because `app.fastapi` is a real FastAPI instance, this is not a PyForge
testing API at all — it's stock `fastapi.testclient.TestClient` (built on
Starlette's `TestClient`/`httpx`). That's deliberate: application tests
should never need framework-specific test knowledge for the parts FastAPI
already covers well.

For code that goes through the container (e.g. a controller with an
injected service), tests can either:

- Go through a real request (`TestClient`), which resolves dependencies
  exactly as production does, or
- Construct a fresh `Container()`, register test doubles with
  `container.instance(SomeService, FakeService())`, and call
  `container.make(SomeController)` directly for a narrower unit test — see
  `tests/test_container.py::test_instance_registers_an_already_built_object`
  for the pattern.

## What's planned (Phase 7, and pulled forward as each subsystem lands)

As Phase 2+ subsystems are built, each needs a corresponding *fake* so tests
don't need real infrastructure:

| Subsystem | Planned test helper |
|---|---|
| Database | a transactional-rollback pytest fixture (each test runs in a transaction that's rolled back, never committed) |
| Events | `Event.fake()` — assert an event was dispatched without running listeners |
| Jobs / queue | `Queue.fake()` — assert a job was pushed without executing it |
| Mail | `Mail.fake()` — assert a mail was "sent" and inspect its content, without a real SMTP connection |
| Notifications | `Notification.fake()` — same pattern as Mail |
| HTTP | a `pyforge-testing` package wrapping common assertions (`assert_status`, `assert_json`) as a thin, optional convenience over `httpx.Response` — never a replacement for it |

None of these exist yet; they are designed alongside their corresponding
subsystem in [09-roadmap.md](09-roadmap.md), not built speculatively ahead
of it, per the project's "no premature abstraction" rule.

## `pyforge test`

There is intentionally no `pyforge test` command in Phase 1: `pytest` already
runs a generated project's test suite with zero extra configuration (see the
CI workflow for proof). A wrapper command will only be introduced if a later
phase needs it to do something `pytest` alone can't (e.g. auto-provisioning
a test database) — see the note in
[04-cli-specification.md](04-cli-specification.md#planned-by-phase--see-09-roadmapmd-for-detail).
