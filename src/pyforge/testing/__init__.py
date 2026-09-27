"""Testing helpers — an *optional* module (``pyforge.testing``), not
imported by ``import pyforge``. Depends on ``pyforge.mail``,
``pyforge.queue``, and ``pyforge.events`` (all optional themselves); import
only the fakes for what you're actually using.

    from pyforge.testing import fake_mail, fake_queue, fake_events, assert_status
"""

from .fakes import FakeEventDispatcher, FakeQueueDriver
from .helpers import assert_json_subset, assert_status, fake_events, fake_mail, fake_queue

__all__ = [
    "FakeEventDispatcher",
    "FakeQueueDriver",
    "assert_json_subset",
    "assert_status",
    "fake_events",
    "fake_mail",
    "fake_queue",
]
