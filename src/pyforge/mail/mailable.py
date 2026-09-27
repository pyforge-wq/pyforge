class Mailable:
    """Base class for a specific email — override ``subject`` and at least
    one of ``html``/``text``::

        class WelcomeEmail(Mailable):
            def __init__(self, user) -> None:
                self.user = user

            def subject(self) -> str:
                return "Welcome!"

            def html(self) -> str:
                return f"<p>Welcome, {self.user.name}!</p>"
    """

    def subject(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} must implement subject().")

    def html(self) -> str | None:
        return None

    def text(self) -> str | None:
        return None
