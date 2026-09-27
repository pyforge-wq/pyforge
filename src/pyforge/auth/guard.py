from __future__ import annotations

from typing import Any

from fastapi import Cookie, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer

from .hashing import hash_password, verify_password
from .jwt import TokenError, decode_token, encode_token


class Auth:
    """Configures JWT + signed-cookie-session authentication for one user
    model. Construct once (typically in a service provider) and reuse its
    dependency methods as FastAPI dependencies::

        auth = Auth(User, secret=config("auth.jwt.secret"))

        class SessionController:
            async def login(self, credentials: LoginRequest) -> dict:
                user = auth.attempt(credentials.email, credentials.password)
                if user is None:
                    raise HTTPException(401, "Invalid credentials")
                return auth.login(user)

            async def me(self, user: Any = Depends(auth.required)) -> dict:
                return {"id": user.id}

    Everything here is one primitive — a signed, expiring JWT with a
    ``purpose`` claim — reused for access tokens, refresh tokens, session
    cookies, and email-verification/password-reset tokens alike. There is
    no separate signing implementation per use case.
    """

    def __init__(
        self,
        user_model: type[Any],
        *,
        secret: str,
        algorithm: str = "HS256",
        access_ttl_minutes: float = 60,
        refresh_ttl_minutes: float = 60 * 24 * 14,
        email_field: str = "email",
        password_field: str = "password_hash",
        login_url: str = "auth/login",
    ) -> None:
        self.user_model = user_model
        self.secret = secret
        self.algorithm = algorithm
        self.access_ttl_minutes = access_ttl_minutes
        self.refresh_ttl_minutes = refresh_ttl_minutes
        self.email_field = email_field
        self.password_field = password_field
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=login_url, auto_error=False)

        async def required(token: str | None = Depends(self.oauth2_scheme)) -> Any:
            user = self._user_for(token, purpose="access")
            if user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return user

        async def optional(token: str | None = Depends(self.oauth2_scheme)) -> Any | None:
            return self._user_for(token, purpose="access")

        async def session_required(session: str | None = Cookie(default=None)) -> Any:
            user = self._user_for(session, purpose="session")
            if user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return user

        self.required = required
        self.optional = optional
        self.session_required = session_required

    # Password hashing, re-exported so app code doesn't need a separate import.
    hash_password = staticmethod(hash_password)
    verify_password = staticmethod(verify_password)

    def attempt(self, email: str, password: str) -> Any | None:
        """Looks up a user by ``email_field`` and verifies ``password``
        against ``password_field``'s stored hash. Returns the user, or
        ``None`` on any failure (unknown email, wrong password)."""
        user = self.user_model.where(self.email_field, email).first()
        if user is None:
            return None
        stored_hash = getattr(user, self.password_field, None)
        if not stored_hash or not verify_password(password, stored_hash):
            return None
        return user

    def _issue(self, user_id: Any, *, purpose: str, ttl_minutes: float) -> str:
        return encode_token(
            {"sub": str(user_id), "purpose": purpose},
            secret=self.secret,
            algorithm=self.algorithm,
            ttl_minutes=ttl_minutes,
        )

    def _user_for(self, token: str | None, *, purpose: str) -> Any | None:
        if not token:
            return None
        try:
            payload = decode_token(token, secret=self.secret, algorithm=self.algorithm)
        except TokenError:
            return None
        if payload.get("purpose") != purpose:
            return None
        return self.user_model.find(payload["sub"])

    def login(self, user: Any) -> dict[str, str]:
        """Issues an access + refresh token pair for an already-authenticated user."""
        return {
            "access_token": self._issue(user.id, purpose="access", ttl_minutes=self.access_ttl_minutes),
            "refresh_token": self._issue(user.id, purpose="refresh", ttl_minutes=self.refresh_ttl_minutes),
            "token_type": "bearer",
        }

    def refresh(self, refresh_token: str) -> dict[str, str]:
        """Exchanges a valid refresh token for a new access token."""
        try:
            payload = decode_token(refresh_token, secret=self.secret, algorithm=self.algorithm)
        except TokenError as exc:
            raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
        if payload.get("purpose") != "refresh":
            raise HTTPException(status_code=401, detail="Not a refresh token")
        return {
            "access_token": self._issue(payload["sub"], purpose="access", ttl_minutes=self.access_ttl_minutes),
            "token_type": "bearer",
        }

    def session_login(self, response: Response, user: Any, *, secure: bool = True) -> None:
        """Cookie-based session authentication: sets an httponly, signed
        session cookie. The stateless counterpart to :meth:`login`.
        ``secure=True`` by default (the cookie is only sent over HTTPS,
        matching production best practice) — pass ``secure=False`` for local
        development over plain ``http://localhost``, where browsers won't
        send a secure cookie back at all."""
        token = self._issue(user.id, purpose="session", ttl_minutes=self.access_ttl_minutes)
        response.set_cookie("session", token, httponly=True, samesite="lax", secure=secure)

    def session_logout(self, response: Response) -> None:
        response.delete_cookie("session")

    def make_signed_token(self, user_id: Any, *, purpose: str, ttl_minutes: float = 60) -> str:
        """Email verification / password reset tokens are the same signed,
        expiring, purpose-tagged JWT as everything else here — sending the
        email itself is a Phase 5 (Mail) concern, not this method's job."""
        return self._issue(user_id, purpose=purpose, ttl_minutes=ttl_minutes)

    def verify_signed_token(self, token: str, *, purpose: str) -> Any | None:
        """Returns the referenced user if ``token`` is valid, unexpired, and
        was issued for ``purpose`` — else ``None``."""
        return self._user_for(token, purpose=purpose)
