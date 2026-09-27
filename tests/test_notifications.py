from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from pyforge.database import DatabaseManager, session_scope, set_current_database
from pyforge.mail import ArrayMailDriver, Mailable, Mailer
from pyforge.notifications import (
    DatabaseNotificationChannel,
    MailChannel,
    Notification,
    NotificationManager,
    notify,
    register_channel,
)
from pyforge.orm import Base, Model


class User(Model):
    __tablename__ = "notif_test_users"

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))


class DatabaseNotification(Model):
    __tablename__ = "notif_test_notifications"

    notifiable_id: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(255))
    data: Mapped[dict] = mapped_column(JSON)


class WelcomeEmail(Mailable):
    def __init__(self, user: Any) -> None:
        self.user = user

    def subject(self) -> str:
        return "Welcome!"

    def html(self) -> str:
        return f"<p>Welcome, {self.user.name}!</p>"


class WelcomeNotification(Notification):
    def via(self, notifiable: Any) -> list[str]:
        return ["mail", "database"]

    def to_mail(self, notifiable: Any) -> Mailable:
        return WelcomeEmail(notifiable)

    def to_database(self, notifiable: Any) -> dict:
        return {"message": f"Welcome, {notifiable.name}!"}


class MailOnlyNotification(Notification):
    def via(self, notifiable: Any) -> list[str]:
        return ["mail"]

    def to_mail(self, notifiable: Any) -> Mailable:
        return WelcomeEmail(notifiable)


@pytest.fixture
def db(tmp_path) -> Iterator[DatabaseManager]:
    manager = DatabaseManager(
        {
            "default": "sqlite",
            "connections": {"sqlite": {"driver": "sqlite", "database": str(tmp_path / "notif.sqlite")}},
        }
    )
    Base.metadata.create_all(manager.engine())
    set_current_database(manager)
    try:
        yield manager
    finally:
        set_current_database(None)
        manager.dispose()


def test_mail_only_notification_sends_via_mail_channel(db: DatabaseManager) -> None:
    array_driver = ArrayMailDriver()
    manager = NotificationManager()
    manager.register_channel("mail", MailChannel(mailer_getter=lambda: Mailer(array_driver, from_address="hello@example.com")))

    with session_scope():
        user = User.create(name="Ada", email="ada@example.com")
        manager.send(user, MailOnlyNotification())

    assert len(array_driver.sent) == 1
    assert array_driver.sent[0].to == ["ada@example.com"]
    assert array_driver.sent[0].subject == "Welcome!"


def test_notification_sends_via_multiple_channels(db: DatabaseManager) -> None:
    array_driver = ArrayMailDriver()
    manager = NotificationManager()
    manager.register_channel("mail", MailChannel(mailer_getter=lambda: Mailer(array_driver, from_address="hello@example.com")))
    manager.register_channel("database", DatabaseNotificationChannel(DatabaseNotification))

    with session_scope():
        user = User.create(name="Ada", email="ada@example.com")
        manager.send(user, WelcomeNotification())

    assert len(array_driver.sent) == 1

    with session_scope():
        records = DatabaseNotification.all()
        assert len(records) == 1
        assert records[0].notifiable_id == user.id
        assert records[0].type == "WelcomeNotification"
        assert records[0].data == {"message": "Welcome, Ada!"}


def test_missing_channel_raises_key_error(db: DatabaseManager) -> None:
    manager = NotificationManager()
    manager._channels.pop("mail", None)

    with session_scope(), pytest.raises(KeyError):
        user = User.create(name="Ada", email="ada@example.com")
        manager.send(user, MailOnlyNotification())


def test_global_notify_and_register_channel_helpers(db: DatabaseManager) -> None:
    array_driver = ArrayMailDriver()
    register_channel("mail", MailChannel(mailer_getter=lambda: Mailer(array_driver, from_address="hello@example.com")))
    try:
        with session_scope():
            user = User.create(name="Ada", email="ada@example.com")
            notify(user, MailOnlyNotification())
        assert len(array_driver.sent) == 1
    finally:
        import pyforge.notifications.helpers as helpers_module

        helpers_module._default_manager = NotificationManager()
