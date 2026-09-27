# Mail & Notifications

## Mail (`pyforge.mail`)

```python
from pyforge.mail import Mailable, make_mailer, set_default_mailer, mail

class WelcomeEmail(Mailable):
    def __init__(self, user) -> None:
        self.user = user

    def subject(self) -> str:
        return "Welcome!"

    def html(self) -> str:
        return f"<p>Welcome, {self.user.name}!</p>"
```

```python
set_default_mailer(make_mailer(config("mail")))   # in a service provider
mail().to(user.email).send(WelcomeEmail(user))
```

Drivers, selected via `config("mail")`:

- **`SmtpMailDriver`** — stdlib `smtplib`, no extra dependency. Real
  connection to whatever `MAIL_HOST`/`MAIL_PORT`/credentials you configure.
- **`ArrayMailDriver`** — captures sent messages in `.sent` instead of
  actually sending anything. Set `config = {"default": "array"}` in tests.

No SES/Mailgun/Postmark/SendGrid adapters exist yet — each of those is a
distinct HTTP API, not an SMTP-driver variant, so they're separate,
not-yet-started work rather than a gap in the SMTP driver itself.

## Notifications (`pyforge.notifications`)

Built on top of `pyforge.mail` — a notification is just a router over one or
more delivery channels, and `"mail"` is one of them:

```python
from pyforge.notifications import Notification, notify, register_channel, DatabaseNotificationChannel

class WelcomeNotification(Notification):
    def via(self, notifiable) -> list[str]:
        return ["mail", "database"]

    def to_mail(self, notifiable) -> Mailable:
        return WelcomeEmail(notifiable)

    def to_database(self, notifiable) -> dict:
        return {"message": "Welcome!"}
```

```python
register_channel("database", DatabaseNotificationChannel(YourNotificationModel))
notify(user, WelcomeNotification())
```

- The `"mail"` channel is registered **by default** — no setup needed beyond
  having a mailer configured.
- The `"database"` channel needs your own model (same reasoning as
  `ApiTokenAuth`'s token table — the shape is an app decision, not fixed by
  the framework):

```python
class YourNotificationModel(Model):
    __tablename__ = "notifications"
    notifiable_id: Mapped[int]
    data: Mapped[dict] = mapped_column(JSON)
    read_at: Mapped[datetime | None]
```

No webhook channel exists yet.

## Generate one

```bash
pyforge make:notification WelcomeNotification
```

## Testing without sending real email

See [Testing](testing.md) for `fake_mail()` — installs a recording mailer so
tests can assert an email was "sent" and inspect its content without a real
SMTP connection.
