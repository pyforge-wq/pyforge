import time
from email.message import EmailMessage as StdlibEmailMessage

import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message as MessageHandler

from pyforge.mail import ArrayMailDriver, Mailable, Mailer, SmtpMailDriver, make_mailer


class WelcomeEmail(Mailable):
    def __init__(self, name: str) -> None:
        self.name = name

    def subject(self) -> str:
        return "Welcome!"

    def html(self) -> str:
        return f"<p>Welcome, {self.name}!</p>"


class PlainTextEmail(Mailable):
    def subject(self) -> str:
        return "Plain"

    def text(self) -> str:
        return "Just text."


class EmptyEmail(Mailable):
    def subject(self) -> str:
        return "Empty"


def test_array_driver_captures_sent_messages() -> None:
    mailer = Mailer(ArrayMailDriver(), from_address="hello@example.com")
    mailer.to("ada@example.com").send(WelcomeEmail("Ada"))

    assert len(mailer.driver.sent) == 1
    message = mailer.driver.sent[0]
    assert message.to == ["ada@example.com"]
    assert message.from_address == "hello@example.com"
    assert message.subject == "Welcome!"
    assert message.html == "<p>Welcome, Ada!</p>"


def test_pending_mail_supports_cc_and_bcc() -> None:
    mailer = Mailer(ArrayMailDriver(), from_address="hello@example.com")
    mailer.to("ada@example.com").cc("cc@example.com").bcc("bcc@example.com").send(WelcomeEmail("Ada"))

    message = mailer.driver.sent[0]
    assert message.cc == ["cc@example.com"]
    assert message.bcc == ["bcc@example.com"]


def test_make_mailer_array_driver() -> None:
    mailer = make_mailer({"default": "array", "from_address": "a@example.com"})
    assert isinstance(mailer.driver, ArrayMailDriver)
    assert mailer.from_address == "a@example.com"


def test_make_mailer_unknown_driver_raises() -> None:
    with pytest.raises(ValueError):
        make_mailer({"default": "not-a-driver"})


class _CollectingHandler(MessageHandler):
    def __init__(self) -> None:
        self.messages: list = []
        super().__init__(message_class=StdlibEmailMessage)

    def handle_message(self, message) -> None:
        self.messages.append(message)


def _find_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def smtp_server():
    handler = _CollectingHandler()
    port = _find_free_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    time.sleep(0.1)
    try:
        yield controller.hostname, port, handler
    finally:
        controller.stop()


def test_smtp_driver_sends_a_real_message_over_the_wire(smtp_server) -> None:
    host, port, handler = smtp_server
    driver = SmtpMailDriver(host=host, port=port)
    mailer = Mailer(driver, from_address="hello@example.com")

    mailer.to("ada@example.com").send(WelcomeEmail("Ada"))

    assert len(handler.messages) == 1
    received = handler.messages[0]
    assert received["Subject"] == "Welcome!"
    assert received["From"] == "hello@example.com"
    assert received["To"] == "ada@example.com"
    body = received.get_body(preferencelist=("html",))
    assert "Welcome, Ada!" in body.get_payload(decode=True).decode()


def test_smtp_driver_sends_plain_text(smtp_server) -> None:
    host, port, handler = smtp_server
    driver = SmtpMailDriver(host=host, port=port)
    mailer = Mailer(driver, from_address="hello@example.com")

    mailer.to("ada@example.com").send(PlainTextEmail())

    assert len(handler.messages) == 1
    body = handler.messages[0].get_body(preferencelist=("plain",))
    assert "Just text." in body.get_payload(decode=True).decode()


def test_smtp_driver_raises_if_mailable_has_no_content(smtp_server) -> None:
    host, port, _handler = smtp_server
    driver = SmtpMailDriver(host=host, port=port)
    mailer = Mailer(driver, from_address="hello@example.com")

    with pytest.raises(ValueError):
        mailer.to("ada@example.com").send(EmptyEmail())
