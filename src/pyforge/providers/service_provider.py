from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyforge.core.application import PyForge


class ServiceProvider:
    """Base class for packaging bindings, routes, and boot logic.

    Subclasses override :meth:`register` (bind things into the container —
    must not depend on other providers having run yet) and :meth:`boot`
    (runs after every provider has registered, safe to depend on other
    providers' bindings). This is the extension point packages use to hook
    into a PyForge application: ``app.register(MyPackageProvider)``.
    """

    def __init__(self, app: PyForge) -> None:
        self.app = app

    def register(self) -> None:
        """Bind services into ``self.app.container``. Override as needed."""

    def boot(self) -> None:
        """Run after all providers have registered. Override as needed."""
