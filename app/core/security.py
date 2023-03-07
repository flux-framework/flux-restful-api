from datetime import datetime, timedelta
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expires_minutes
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify the password
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Note we aren't providing a salt here, so the same password can generate different.
    """
    return pwd_context.hash(password)
