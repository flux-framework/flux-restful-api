from datetime import datetime, timedelta, timezone
from typing import Any, Union

import bcrypt
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"

# bcrypt silently ignored bytes past 72 in older versions and raises in >= 5.0.
# We reject longer passwords explicitly so behavior is the same everywhere.
MAX_PASSWORD_BYTES = 72


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None, secret_key=None
) -> str:
    """
    Create a jwt access token.

    We either use the user's secret key (which is hashed) or fall
    back to the server set secret key.
    """
    # Use a user secret key, if they have one.
    # Otherwise fall back to server secret key
    secret_key = secret_key or settings.secret_key
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expires_minutes)
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password cannot be longer than {MAX_PASSWORD_BYTES} bytes.")
    return encoded


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Over-long password or malformed stored hash: never a match
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password with bcrypt (a random salt is generated per hash).
    """
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")
