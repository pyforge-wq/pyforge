import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyforge.events import event, listen
from pyforge.mail import Mailable, default_mailer
from pyforge.queue import Job, dispatch
from pyforge.testing import assert_json_subset, assert_status, fake_events, fake_mail, fake_queue


class WelcomeEmail(Mailable):
    def subject(self) -> str:
        return "Welcome!"

    def text(self) -> str:
        return "hi"


class SendWelcomeEmail(Job):
    def handle(self) -> None:
        raise AssertionError("This job should never actually run when faked.")


class OtherJob(Job):
    def handle(self) -> None:
        pass


class UserRegistered:
    pass


class OtherEvent:
    pass


def test_fake_mail_captures_without_sending() -> None:
    fake = fake_mail()
    default_mailer().to("ada@example.com").send(WelcomeEmail())
    assert len(fake.sent) == 1
    assert fake.sent[0].subject == "Welcome!"


def test_fake_queue_records_without_running() -> None:
    fake = fake_queue()
    dispatch(SendWelcomeEmail())  # would raise if it actually ran
    fake.assert_pushed(SendWelcomeEmail)
    fake.assert_not_pushed(OtherJob)


def test_fake_queue_assert_pushed_raises_when_missing() -> None:
    fake = fake_queue()
    with pytest.raises(AssertionError):
        fake.assert_pushed(SendWelcomeEmail)


def test_fake_queue_assert_not_pushed_raises_when_present() -> None:
    fake = fake_queue()
    dispatch(SendWelcomeEmail())
    with pytest.raises(AssertionError):
        fake.assert_not_pushed(SendWelcomeEmail)


@pytest.mark.asyncio
async def test_fake_events_records_without_running_listeners() -> None:
    fake = fake_events()
    ran = []
    listen(UserRegistered, lambda e: ran.append(1))

    await event(UserRegistered())

    fake.assert_dispatched(UserRegistered)
    fake.assert_not_dispatched(OtherEvent)
    assert ran == []  # listener never actually invoked


@pytest.mark.asyncio
async def test_fake_events_assert_dispatched_raises_when_missing() -> None:
    fake = fake_events()
    with pytest.raises(AssertionError):
        fake.assert_dispatched(UserRegistered)


def test_assert_status_passes_and_fails() -> None:
    app = FastAPI()

    @app.get("/ok")
    async def ok() -> dict:
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.get("/ok")
        assert_status(response, 200)
        with pytest.raises(AssertionError):
            assert_status(response, 404)


def test_assert_json_subset() -> None:
    app = FastAPI()

    @app.get("/user")
    async def user() -> dict:
        return {"id": 1, "name": "Ada", "email": "ada@example.com"}

    with TestClient(app) as client:
        response = client.get("/user")
        assert_json_subset(response, {"name": "Ada"})
        with pytest.raises(AssertionError):
            assert_json_subset(response, {"name": "Wrong"})
        with pytest.raises(AssertionError):
            assert_json_subset(response, {"missing_key": "x"})
