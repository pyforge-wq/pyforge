from __future__ import annotations

from typing import Any

from pyforge.events import set_default_dispatcher
from pyforge.mail import ArrayMailDriver, Mailer, set_default_mailer
from pyforge.queue import set_default_queue

from .fakes import FakeEventDispatcher, FakeQueueDriver


def fake_mail(*, from_address: str = "test@example.com") -> ArrayMailDriver:
    """Installs an :class:`~pyforge.mail.ArrayMailDriver` as the default
    mailer and returns it — ``mail().to(...).send(...)`` (and anything else
    using the default mailer) is captured, not actually sent::

        sent = fake_mail()
        response = client.post("/register", json={...})
        assert len(sent.sent) == 1
    """
    driver = ArrayMailDriver()
    set_default_mailer(Mailer(driver, from_address=from_address))
    return driver


def fake_queue() -> FakeQueueDriver:
    """Installs a :class:`~pyforge.testing.FakeQueueDriver` as the default
    queue — ``dispatch(...)`` records the job instead of running it::

        queue = fake_queue()
        response = client.post("/register", json={...})
        queue.assert_pushed(SendWelcomeEmail)
    """
    driver = FakeQueueDriver()
    set_default_queue(driver)
    return driver


def fake_events() -> FakeEventDispatcher:
    """Installs a :class:`~pyforge.testing.FakeEventDispatcher` as the
    default dispatcher — ``await event(...)`` records it instead of running
    listeners::

        events = fake_events()
        response = client.post("/register", json={...})
        events.assert_dispatched(UserRegistered)
    """
    dispatcher = FakeEventDispatcher()
    set_default_dispatcher(dispatcher)
    return dispatcher


def assert_status(response: Any, expected: int) -> None:
    """``assert_status(response, 201)`` — raises with the response body in
    the message on mismatch, instead of just the two status codes."""
    if response.status_code != expected:
        raise AssertionError(
            f"Expected status {expected}, got {response.status_code}. Body: {response.text}"
        )


def assert_json_subset(response: Any, expected: dict[str, Any]) -> None:
    """Asserts every key/value in ``expected`` matches the response's JSON
    body — the body may have additional keys not mentioned in ``expected``."""
    body = response.json()
    for key, value in expected.items():
        if key not in body:
            raise AssertionError(f"Expected key '{key}' in response JSON, got: {body}")
        if body[key] != value:
            raise AssertionError(f"Expected {key}={value!r}, got {key}={body[key]!r}. Full body: {body}")
