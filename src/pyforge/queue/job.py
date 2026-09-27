from typing import ClassVar


class Job:
    """Base class for queued jobs — override ``handle``::

        class SendWelcomeEmail(Job):
            def __init__(self, user_id: int) -> None:
                self.user_id = user_id

            def handle(self) -> None:
                ...

        dispatch(SendWelcomeEmail(user.id))

    Must be picklable for the Redis driver: only plain attributes, no open
    file handles/sessions/connections. Pickling also means the *worker*
    process runs a byte-for-byte copy of the instance you pushed — its
    attributes are captured by value at push time, so a job can't report
    results back to the dispatching process via a shared list/object;
    write results to the database (or another out-of-band store) instead.
    """

    max_retries: ClassVar[int] = 0
    retry_backoff_seconds: ClassVar[float] = 0

    def handle(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement handle().")
