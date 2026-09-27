from __future__ import annotations

from typing import Any

from .drivers import ArrayMailDriver, MailDriver, SmtpMailDriver
from .mailable import Mailable
from .message import Message


class PendingMail:
    """Returned by ``Mailer.to(...)`` — call ``.send(mailable)`` on it."""

    def __init__(self, mailer: Mailer, to: list[str]) -> None:
        self._mailer = mailer
        self._to = to
        self._cc: list[str] = []
        self._bcc: list[str] = []

    def cc(self, *addresses: str) -> PendingMail:
        self._cc.extend(addresses)
        return self

    def bcc(self, *addresses: str) -> PendingMail:
        self._bcc.extend(addresses)
        return self

    def send(self, mailable: Mailable) -> None:
        message = Message(
            to=self._to,
            from_address=self._mailer.from_address,
            subject=mailable.subject(),
            html=mailable.html(),
            text=mailable.text(),
            cc=self._cc,
            bcc=self._bcc,
        )
        self._mailer.driver.send(message)


class Mailer:
    """``Mail.to(user.email).send(WelcomeEmail(user))``."""

    def __init__(self, driver: MailDriver, *, from_address: str) -> None:
        self.driver = driver
        self.from_address = from_address

    def to(self, *recipients: str) -> PendingMail:
        return PendingMail(self, list(recipients))


def make_mailer(config: dict[str, Any]) -> Mailer:
    """Builds a :class:`Mailer` from the same shape as a generated
    project's ``config/mail.py``."""
    driver_name = config.get("default", "smtp")
    from_address = config.get("from_address", "hello@example.com")

    driver: MailDriver
    if driver_name == "smtp":
        driver = SmtpMailDriver(
            host=config.get("host", "localhost"),
            port=config.get("port", 1025),
            username=config.get("username"),
            password=config.get("password"),
            use_tls=config.get("use_tls", False),
        )
    elif driver_name == "array":
        driver = ArrayMailDriver()
    else:
        raise ValueError(f"Unknown mail driver '{driver_name}'.")

    return Mailer(driver, from_address=from_address)
