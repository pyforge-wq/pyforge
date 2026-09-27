from typing import Any


class Notification:
    """Base class for a notification — override ``via`` plus whichever
    ``to_<channel>`` methods it names::

        class WelcomeNotification(Notification):
            def via(self, notifiable) -> list[str]:
                return ["mail", "database"]

            def to_mail(self, notifiable) -> Mailable:
                return WelcomeEmail(notifiable)

            def to_database(self, notifiable) -> dict:
                return {"message": f"Welcome, {notifiable.name}!"}

        notify(user, WelcomeNotification())
    """

    def via(self, notifiable: Any) -> list[str]:
        raise NotImplementedError(f"{type(self).__name__} must implement via().")

    def to_mail(self, notifiable: Any) -> Any:
        raise NotImplementedError(f"{type(self).__name__} must implement to_mail() to use the 'mail' channel.")

    def to_database(self, notifiable: Any) -> dict[str, Any]:
        raise NotImplementedError(
            f"{type(self).__name__} must implement to_database() to use the 'database' channel."
        )
