"""Events — an *optional* module (``pyforge.events``), not imported by
``import pyforge``.

    from pyforge.events import event, listen, Listener
"""

from .dispatcher import EventDispatcher
from .helpers import default_dispatcher, event, listen, set_default_dispatcher
from .listener import Listener

__all__ = ["EventDispatcher", "Listener", "default_dispatcher", "event", "listen", "set_default_dispatcher"]
