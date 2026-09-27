from __future__ import annotations

from typing import Any

from .channels import MailChannel, NotificationChannel
from .notification import Notification


class NotificationManager:
    """Maps channel names (as returned by ``Notification.via(...)``) to
    :class:`NotificationChannel` instances. ``"mail"`` is registered by
    default (backed by whichever `Mailer` :func:`pyforge.mail.default_mailer`
    resolves at send time); register ``"database"`` yourself with your own
    notifications model — see :class:`~pyforge.notifications.DatabaseNotificationChannel`.
    """

    def __init__(self) -> None:
        self._channels: dict[str, NotificationChannel] = {"mail": MailChannel()}

    def register_channel(self, name: str, channel: NotificationChannel) -> None:
        self._channels[name] = channel

    def send(self, notifiable: Any, notification: Notification) -> None:
        for channel_name in notification.via(notifiable):
            channel = self._channels.get(channel_name)
            if channel is None:
                raise KeyError(
                    f"No notification channel registered for '{channel_name}'. "
                    "Call register_channel(...) first."
                )
            channel.send(notifiable, notification)
