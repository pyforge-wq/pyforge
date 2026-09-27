from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyforge.mail import Mailer

    from .notification import Notification


class NotificationChannel:
    def send(self, notifiable: Any, notification: Notification) -> None:
        raise NotImplementedError


class MailChannel(NotificationChannel):
    """Delivers a notification's ``to_mail(notifiable)`` via the default
    :class:`~pyforge.mail.Mailer` (see :func:`pyforge.mail.default_mailer`),
    to whatever attribute on ``notifiable`` holds its email address."""

    def __init__(self, mailer_getter: Callable[[], Mailer] | None = None, *, email_field: str = "email") -> None:
        self._mailer_getter = mailer_getter
        self.email_field = email_field

    def _mailer(self) -> Mailer:
        if self._mailer_getter is not None:
            return self._mailer_getter()
        from pyforge.mail import default_mailer

        return default_mailer()

    def send(self, notifiable: Any, notification: Notification) -> None:
        mailable = notification.to_mail(notifiable)
        email = getattr(notifiable, self.email_field)
        self._mailer().to(email).send(mailable)


class DatabaseNotificationChannel(NotificationChannel):
    """Persists ``to_database(notifiable)`` via whatever ``Model`` the app
    defines for storing notifications — deliberately not a fixed abstract
    base (same reasoning as :class:`pyforge.auth.ApiTokenAuth`): a
    notifications table's exact shape is an app decision."""

    def __init__(
        self,
        notification_model: type[Any],
        *,
        notifiable_id_field: str = "notifiable_id",
        type_field: str = "type",
        data_field: str = "data",
    ) -> None:
        self.notification_model = notification_model
        self.notifiable_id_field = notifiable_id_field
        self.type_field = type_field
        self.data_field = data_field

    def send(self, notifiable: Any, notification: Notification) -> None:
        data = notification.to_database(notifiable)
        self.notification_model.create(
            **{
                self.notifiable_id_field: notifiable.id,
                self.type_field: type(notification).__name__,
                self.data_field: data,
            }
        )
