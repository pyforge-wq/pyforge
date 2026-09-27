from __future__ import annotations

from .mailer import Mailer

_default_mailer: Mailer | None = None


def set_default_mailer(mailer: Mailer) -> None:
    """Registers the process-wide default ``Mailer`` — typically from a
    service provider's ``register()``, right after :func:`make_mailer`."""
    global _default_mailer
    _default_mailer = mailer


def default_mailer() -> Mailer:
    if _default_mailer is None:
        raise RuntimeError(
            "No default Mailer configured. Call set_default_mailer(make_mailer(config('mail'))) "
            "once, e.g. from a service provider's register()."
        )
    return _default_mailer


def mail() -> Mailer:
    """Shorthand for ``default_mailer()`` — ``mail().to(user.email).send(...)``."""
    return default_mailer()
