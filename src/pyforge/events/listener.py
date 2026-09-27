class Listener:
    """Base class for event listeners — override ``handle`` (sync or
    ``async def``, both work)::

        class SendWelcomeEmail(Listener):
            async def handle(self, event: UserRegistered) -> None:
                ...
    """

    def handle(self, event: object) -> object:
        raise NotImplementedError(f"{type(self).__name__} must implement handle().")
