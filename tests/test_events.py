import pytest

from pyforge.events import EventDispatcher, Listener, event, listen


class UserRegistered:
    def __init__(self, name: str) -> None:
        self.name = name


class OtherEvent:
    pass


@pytest.fixture(autouse=True)
def _clean_default_dispatcher():
    import pyforge.events.helpers as helpers_module

    original = helpers_module._default_dispatcher
    helpers_module._default_dispatcher = EventDispatcher()
    yield
    helpers_module._default_dispatcher = original


def test_sync_listener_runs() -> None:
    dispatcher = EventDispatcher()
    received = []

    def handler(evt: UserRegistered) -> None:
        received.append(evt.name)

    dispatcher.listen(UserRegistered, handler)

    import asyncio

    asyncio.run(dispatcher.dispatch(UserRegistered("Ada")))
    assert received == ["Ada"]


def test_async_listener_is_awaited() -> None:
    dispatcher = EventDispatcher()
    received = []

    async def handler(evt: UserRegistered) -> None:
        received.append(evt.name)

    dispatcher.listen(UserRegistered, handler)

    import asyncio

    asyncio.run(dispatcher.dispatch(UserRegistered("Ada")))
    assert received == ["Ada"]


def test_listener_class_is_instantiated_per_dispatch() -> None:
    dispatcher = EventDispatcher()
    received = []

    class SendWelcomeEmail(Listener):
        async def handle(self, evt: UserRegistered) -> None:
            received.append(evt.name)

    dispatcher.listen(UserRegistered, SendWelcomeEmail)

    import asyncio

    asyncio.run(dispatcher.dispatch(UserRegistered("Ada")))
    asyncio.run(dispatcher.dispatch(UserRegistered("Alan")))
    assert received == ["Ada", "Alan"]


def test_multiple_listeners_all_run() -> None:
    dispatcher = EventDispatcher()
    received = []

    dispatcher.listen(UserRegistered, lambda e: received.append(f"first:{e.name}"))
    dispatcher.listen(UserRegistered, lambda e: received.append(f"second:{e.name}"))

    import asyncio

    asyncio.run(dispatcher.dispatch(UserRegistered("Ada")))
    assert received == ["first:Ada", "second:Ada"]


def test_listener_for_unrelated_event_does_not_run() -> None:
    dispatcher = EventDispatcher()
    received = []

    dispatcher.listen(OtherEvent, lambda e: received.append("should not run"))
    dispatcher.listen(UserRegistered, lambda e: received.append("ran"))

    import asyncio

    asyncio.run(dispatcher.dispatch(UserRegistered("Ada")))
    assert received == ["ran"]


@pytest.mark.asyncio
async def test_global_event_and_listen_helpers() -> None:
    received = []
    listen(UserRegistered, lambda e: received.append(e.name))
    await event(UserRegistered("Ada"))
    assert received == ["Ada"]
