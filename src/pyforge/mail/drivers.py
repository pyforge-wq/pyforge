from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .message import Message


class MailDriver:
    def send(self, message: Message) -> None:
        raise NotImplementedError


class SmtpMailDriver(MailDriver):
    """A thin wrapper over stdlib ``smtplib`` — no mail-sending logic
    reinvented here, just message assembly."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send(self, message: Message) -> None:
        email_message = EmailMessage()
        email_message["Subject"] = message.subject
        email_message["From"] = message.from_address
        email_message["To"] = ", ".join(message.to)
        if message.cc:
            email_message["Cc"] = ", ".join(message.cc)

        if message.text:
            email_message.set_content(message.text)
        if message.html:
            if message.text:
                email_message.add_alternative(message.html, subtype="html")
            else:
                email_message.set_content(message.html, subtype="html")
        if not message.text and not message.html:
            raise ValueError("A Mailable must provide html() and/or text().")

        all_recipients = [*message.to, *message.cc, *message.bcc]

        with smtplib.SMTP(self.host, self.port) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username is not None:
                smtp.login(self.username, self.password or "")
            smtp.send_message(email_message, to_addrs=all_recipients)


class ArrayMailDriver(MailDriver):
    """Captures sent messages instead of actually sending them — the
    testing driver: ``config = {"default": "array", ...}``, then assert
    against ``mailer.driver.sent``."""

    def __init__(self) -> None:
        self.sent: list[Message] = []

    def send(self, message: Message) -> None:
        self.sent.append(message)
