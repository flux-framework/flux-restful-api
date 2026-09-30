"""
Server-issued access tokens.

Tokens are signed with FLUX_TOKEN_SIGNING_KEY, which only the server knows.
This is deliberately a different key from FLUX_SECRET_KEY: that one is shared
with clients for the token handshake, so it must never be able to mint tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


class TokenError(Exception):
    """The token is malformed, expired, or not signed by this server."""


def create_access_token(
    subject: str, backend: str, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed access token for a subject (username).
    """
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expires_minutes)
    payload = {
        "sub": str(subject),
        "backend": backend,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.token_signing_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a token issued by this server. Raises TokenError.
    """
    try:
        return jwt.decode(token, settings.token_signing_key, algorithms=[ALGORITHM])
    except jwt.JWTError as e:
        raise TokenError(str(e)) from e
