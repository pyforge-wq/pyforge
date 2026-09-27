from __future__ import annotations

import hashlib
import secrets
from typing import Any

from fastapi import Header, HTTPException


def generate_api_token() -> tuple[str, str]:
    """Returns ``(plaintext, sha256_hash)`` — show the plaintext to the user
    exactly once (e.g. in an "issue token" API response), store only the
    hash. Never store a raw API token — this isn't a password (no need for
    bcrypt's deliberately-slow hashing here), but it must never be
    recoverable from the database either."""
    plaintext = secrets.token_urlsafe(40)
    digest = hash_api_token(plaintext)
    return plaintext, digest


def hash_api_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class ApiTokenAuth:
    """API-token authentication (Sanctum-style personal access
    tokens), wired to whatever token/user models the app defines::

        class PersonalAccessToken(Model):
            __tablename__ = "personal_access_tokens"
            user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
            token_hash: Mapped[str] = mapped_column(String(64), unique=True)

        api_tokens = ApiTokenAuth(PersonalAccessToken, User)

        class TokenController:
            async def store(self, user: Any = Depends(auth.required)) -> dict:
                return {"token": api_tokens.issue(user)}  # shown once

        class ProfileController:
            async def me(self, user: Any = Depends(api_tokens.required)) -> dict:
                return {"id": user.id}

    Deliberately not a fixed abstract ``Model`` base: the token table's
    exact shape (extra columns like a name, `last_used_at`, expiry, ...) is
    left to the app, since forcing one schema on every project would be the
    kind of premature abstraction this project's own ground rules warn
    against — this class only needs to know two field names.
    """

    def __init__(
        self,
        token_model: type[Any],
        user_model: type[Any],
        *,
        token_field: str = "token_hash",
        user_id_field: str = "user_id",
    ) -> None:
        self.token_model = token_model
        self.user_model = user_model
        self.token_field = token_field
        self.user_id_field = user_id_field

        async def required(authorization: str | None = Header(default=None)) -> Any:
            token = self._extract_bearer(authorization)
            if token is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            record = self.token_model.where(self.token_field, hash_api_token(token)).first()
            if record is None:
                raise HTTPException(status_code=401, detail="Invalid API token")
            user = self.user_model.find(getattr(record, self.user_id_field))
            if user is None:
                raise HTTPException(status_code=401, detail="Invalid API token")
            return user

        self.required = required

    @staticmethod
    def _extract_bearer(header: str | None) -> str | None:
        if not header:
            return None
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return token

    def issue(self, user: Any) -> str:
        """Creates and persists a new token record for ``user``, returning
        the plaintext — the only time it's ever available."""
        plaintext, digest = generate_api_token()
        self.token_model.create(**{self.user_id_field: user.id, self.token_field: digest})
        return plaintext
