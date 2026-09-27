from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from .listener import Listener

ListenerLike = type[Listener] | Callable[[Any], Any]


class EventDispatcher:
    """Maps event types to listeners and runs them on dispatch — plain
    objects, not queued: a listener registered here always runs inline,
    synchronously with respect to the dispatch call (awaited if it's a
    coroutine). Queued/deferred listeners are a queue-system concern
    (Phase 5's queue module), layered on top of this, not built into it.
    """

    def __init__(self) -> None:
        self._listeners: dict[type, list[ListenerLike]] = {}

    def listen(self, event_type: type, listener: ListenerLike) -> None:
        self._listeners.setdefault(event_type, []).append(listener)

    async def dispatch(self, event: object) -> None:
        for event_type, listeners in list(self._listeners.items()):
            if not isinstance(event, event_type):
                continue
            for listener in listeners:
                handler: Callable[[object], Any]
                if isinstance(listener, type):
                    handler = listener().handle
                else:
                    handler = listener
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
