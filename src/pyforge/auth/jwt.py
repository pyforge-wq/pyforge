from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as _pyjwt


class TokenError(Exception):
    """Raised for any expired/malformed/invalid-signature token."""


def encode_token(
    payload: dict[str, Any], *, secret: str, algorithm: str = "HS256", ttl_minutes: float | None = None
) -> str:
    to_encode = dict(payload)
    now = datetime.now(timezone.utc)
    to_encode["iat"] = now
    if ttl_minutes is not None:
        to_encode["exp"] = now + timedelta(minutes=ttl_minutes)
    return _pyjwt.encode(to_encode, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str = "HS256") -> dict[str, Any]:
    try:
        return _pyjwt.decode(token, secret, algorithms=[algorithm])
    except _pyjwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
