import logging
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBasic()


def not_authenticated(detail="Incorrect user or token."):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Basic"},
    )


def alert_auth():
    print("🍓 Require auth: %s" % settings.require_auth)
    print("🍓     PAM auth: %s" % settings.enable_pam)
    print(
        "🍓    Flux user: %s" % ("*" * len(settings.flux_user))
        if settings.flux_user
        else "🍓    Flux user: unset"
    )
    print(
        "🍓   Flux token: %s" % ("*" * len(settings.flux_token))
        if settings.flux_token
        else "🍓   Flux token: unset"
    )


def check_pam_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Check base64 encoded auth (this is HTTP Basic auth.)
    """
    # Ensure we have pam installed
    try:
        import pam
    except ImportError:
        print("python-pam is required for PAM.")
        return

    username = credentials.username.encode("utf8")
    password = credentials.password.encode("utf8")
    if pam.authenticate(username, password) is True:
        return credentials.username


def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Check base64 encoded auth (this is HTTP Basic auth.)
    """
    # First try to authenticate with PAM, if allowed.
    if settings.enable_pam:
        print("🧾️ Checking PAM auth...")
        # Return the username if PAM authentication is successful
        username = check_pam_auth(credentials)
        if username:
            print("🧾️ Success!")
            return username

    # If we get here, we require the flux user and token
    if not settings.flux_user or not settings.flux_token:
        return not_authenticated("Missing FLUX_USER and/or FLUX_TOKEN or pam headers")

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
