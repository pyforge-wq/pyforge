from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (never rolled by hand — see
    docs/architecture's security ground rules). Returns a self-contained
    string (algorithm + cost + salt + hash) safe to store as-is."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time comparison against a hash produced by :func:`hash_password`."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False
