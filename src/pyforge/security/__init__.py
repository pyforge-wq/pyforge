"""Security — an *optional* module (``pyforge.security``), not imported by
``import pyforge``. ``rate_limit`` depends on ``pyforge.cache``.

    from pyforge.security import rate_limit, SecurityHeadersMiddleware
"""

from .headers import SecurityHeadersMiddleware
from .rate_limit import rate_limit

__all__ = ["SecurityHeadersMiddleware", "rate_limit"]
