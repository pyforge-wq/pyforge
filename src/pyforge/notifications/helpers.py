from __future__ import annotations

from typing import Any

from .channels import NotificationChannel
from .manager import NotificationManager
from .notification import Notification

_default_manager = NotificationManager()


def register_channel(name: str, channel: NotificationChannel) -> None:
    """Registers a channel (e.g. ``"database"``) against the process-wide
    default manager. ``"mail"`` is already registered by default."""
    _default_manager.register_channel(name, channel)


def notify(notifiable: Any, notification: Notification) -> None:
    """``notify(user, WelcomeNotification())`` — sends through every channel
    ``notification.via(notifiable)`` names."""
    _default_manager.send(notifiable, notification)
