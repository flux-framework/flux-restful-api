from fastapi import HTTPException, Depends, status
from app.core.config import settings

from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import logging

logger = logging.getLogger(__name__)

security = HTTPBasic()


def not_authenticated(detail="Incorrect user or token."):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Basic"},
    )


def alert_auth():
    print("🍓 Require auth: %s" % settings.flux_require_auth)
    print(
        "🍓    Flux user: %s" % ("*" * len(settings.flux_user))
        if settings.flux_user
        else "unset"
    )
    print(
        "🍓   Flux token: %s" % ("*" * len(settings.flux_token))
        if settings.flux_token
        else "unset"
    )


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not settings.flux_user or not settings.flux_token:
        return not_authenticated("Missing FLUX_USER and/or FLUX_TOKEN")
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = bytes(settings.flux_user.encode("utf8"))
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = bytes(settings.flux_token.encode("utf8"))
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        return not_authenticated()
    return credentials.username


async def get_basic_header(authentication):
    if not authentication:
        raise HTTPException(status_code=400, detail="Authentication header invalid")
