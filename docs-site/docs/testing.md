# Testing

## Testing a PyForge application

Every generated project ships a real, passing test out of the box
(`tests/test_welcome.py`), demonstrating the pattern:

```python
from fastapi.testclient import TestClient
from main import app

def test_health() -> None:
    client = TestClient(app.fastapi)
    response = client.get("/api/health")
    assert response.status_code == 200
```

Because `app.fastapi` is a real FastAPI instance, this is stock
`fastapi.testclient.TestClient` (built on Starlette's `TestClient`/`httpx`) —
not a PyForge-specific testing API. Application tests never need
framework-specific knowledge for the parts FastAPI already covers well.

```bash
pytest
```

## `pyforge.testing`: fakes and assertion helpers

An optional module (`from pyforge.testing import ...`, no extra dependency)
providing recording fakes for mail, queue, and events, plus small assertion
helpers over an `httpx.Response`.

```python
from pyforge.testing import fake_mail, fake_queue, fake_events, assert_status, assert_json_subset

def test_registration_sends_welcome_email_and_dispatches_event():
    sent = fake_mail()
    queue = fake_queue()
    events = fake_events()

    response = client.post("/register", json={"email": "ada@example.com", "password": "s3cret123"})

    assert_status(response, 201)
    assert_json_subset(response, {"email": "ada@example.com"})
    queue.assert_pushed(SendWelcomeEmail)
    events.assert_dispatched(UserRegistered)
```

| Helper | What it does |
|---|---|
| `fake_mail(*, from_address="test@example.com")` | Installs an `ArrayMailDriver` as the default mailer and returns it — `mail().to(...).send(...)` is captured in `.sent`, not actually sent |
| `fake_queue()` | Installs a `FakeQueueDriver` as the default queue and returns it — `dispatch(...)` records the job instead of running it |
| `fake_events()` | Installs a `FakeEventDispatcher` as the default dispatcher and returns it — `await event(...)` records it instead of running listeners |
| `assert_status(response, expected)` | Raises with the response body in the message on mismatch, instead of just the two status codes |
| `assert_json_subset(response, expected)` | Asserts every key/value in `expected` matches the response's JSON — the body may have extra keys not mentioned |

### Asserting on the fakes

```python
queue = fake_queue()
...
queue.assert_pushed(SendWelcomeEmail)
queue.assert_not_pushed(SendPasswordResetEmail)
```

```python
events = fake_events()
...
events.assert_dispatched(UserRegistered)
events.assert_not_dispatched(UserDeleted)
```

```python
sent = fake_mail()
...
assert len(sent.sent) == 1
assert sent.sent[0].subject() == "Welcome!"
```

Each fake is installed as the process-wide default the same way a real
driver would be (`set_default_mailer`/`set_default_queue`/
`set_default_dispatcher`) — application code under test doesn't need to know
it's talking to a fake.

## Testing code that goes through the container

For a controller with an injected service, either:

- Go through a real request (`TestClient`), which resolves dependencies
  exactly as production does, or
- Construct a fresh `Container()`, register test doubles with
  `container.instance(SomeService, FakeService())`, and call
  `container.make(SomeController)` directly for a narrower unit test:

```python
def test_checkout_uses_the_fake_gateway():
    test_container = Container()
    test_container.instance(PaymentGateway, FakeGateway())
    service = test_container.make(CheckoutService)
    ...
```

See [Dependency Injection & Config](dependency-injection-and-config.md#test-isolation).

## Testing the database layer

There's no built-in transactional-rollback fixture yet. The pattern used by
PyForge's own test suite — build a fresh `DatabaseManager` against a
temporary SQLite file per test, and tear it down after:

```python
import pytest
from pyforge.database import DatabaseManager, set_current_database
from pyforge.orm import Base

@pytest.fixture
def db(tmp_path):
    manager = DatabaseManager({
        "default": "sqlite",
        "connections": {"sqlite": {"driver": "sqlite", "database": str(tmp_path / "test.sqlite")}},
    })
    Base.metadata.create_all(manager.engine())
    set_current_database(manager)
    try:
        yield manager
    finally:
        set_current_database(None)
        manager.dispose()
```

## What's not built yet

A transactional-rollback pytest fixture (each test running inside a
transaction that's rolled back rather than committed) isn't shipped — the
fixture above (a fresh SQLite file per test) is the documented pattern in
the meantime.

## Testing a package you're building

If you're authoring your own `pyforge-*` package, test it against a minimal
`PyForge()` instance, never against a real generated project — see
[Extending PyForge](packages.md).
