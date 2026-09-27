"""Mail — an *optional* module (``pyforge.mail``), not imported by
``import pyforge``. No extra dependency: the SMTP driver is stdlib
``smtplib``.

    from pyforge.mail import Mailable, make_mailer, set_default_mailer, mail
"""

from .defaults import default_mailer, mail, set_default_mailer
from .drivers import ArrayMailDriver, MailDriver, SmtpMailDriver
from .mailable import Mailable
from .mailer import Mailer, PendingMail, make_mailer
from .message import Message

__all__ = [
    "ArrayMailDriver",
    "MailDriver",
    "Mailable",
    "Mailer",
    "Message",
    "PendingMail",
    "SmtpMailDriver",
    "default_mailer",
    "mail",
    "make_mailer",
    "set_default_mailer",
]
