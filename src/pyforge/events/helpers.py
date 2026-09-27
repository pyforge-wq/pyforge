from __future__ import annotations

from .dispatcher import EventDispatcher, ListenerLike

_default_dispatcher = EventDispatcher()


def set_default_dispatcher(dispatcher: EventDispatcher) -> None:
    """Swaps the process-wide default dispatcher — what ``pyforge.testing``'s
    ``fake_events()`` uses to install a :class:`~pyforge.testing.FakeEventDispatcher`
    that records dispatches instead of running listeners."""
    global _default_dispatcher
    _default_dispatcher = dispatcher


def default_dispatcher() -> EventDispatcher:
    return _default_dispatcher


def listen(event_type: type, listener: ListenerLike) -> None:
    """Registers ``listener`` (a :class:`~pyforge.events.Listener` subclass,
    or any callable taking the event) against the process-wide default
    dispatcher. Typically called from a service provider's ``boot()``."""
    _default_dispatcher.listen(event_type, listener)


async def event(instance: object) -> None:
    """Dispatches ``instance`` to every listener registered for its type —
    ``await event(UserRegistered(user))``. Async, not the sync-looking call
    in the original spec: dispatch always runs from already-``async def``
    request-handling code here, and some listeners are legitimately
    ``async def`` too (an email send, a webhook call), so making this
    ``await``-able is the honest, async-first shape rather than reaching for
    ``asyncio.run()`` (which breaks inside an already-running event loop —
    exactly where this is always called from)."""
    await _default_dispatcher.dispatch(instance)
