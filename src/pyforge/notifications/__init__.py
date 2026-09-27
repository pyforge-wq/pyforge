"""Notifications — an *optional* module (``pyforge.notifications``), not
imported by ``import pyforge``. The mail channel uses ``pyforge.mail``.

    from pyforge.notifications import Notification, notify, register_channel
"""

from .channels import DatabaseNotificationChannel, MailChannel, NotificationChannel
from .helpers import notify, register_channel
from .manager import NotificationManager
from .notification import Notification

__all__ = [
    "DatabaseNotificationChannel",
    "MailChannel",
    "Notification",
    "NotificationChannel",
    "NotificationManager",
    "notify",
    "register_channel",
]
