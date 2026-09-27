"""Authentication & authorization — an *optional* module (``pyforge.auth``),
not imported by ``import pyforge`` itself, and not wired into ``PyForge``
automatically. See docs/architecture/03-public-api-design.md for the full
picture, and docs/architecture/05-plugin-package-architecture.md for why
this ships inside the same distribution today rather than as a separate
``pyforge-auth`` package: in short, splitting it out is mechanical (it
depends on nothing here that a separate package couldn't depend on too)
and will happen before `1.0` once there's a second real consumer to
validate the package boundary against.

    from pyforge.auth import Auth, ApiTokenAuth, Policy, authorize, role, permission
"""

from .authorization import (
    Policy,
    authorize,
    current_user,
    default_auth,
    permission,
    role,
    set_default_auth,
)
from .guard import Auth
from .hashing import hash_password, verify_password
from .tokens import ApiTokenAuth, generate_api_token, hash_api_token

__all__ = [
    "ApiTokenAuth",
    "Auth",
    "Policy",
    "authorize",
    "current_user",
    "default_auth",
    "generate_api_token",
    "hash_api_token",
    "hash_password",
    "permission",
    "role",
    "set_default_auth",
    "verify_password",
]
