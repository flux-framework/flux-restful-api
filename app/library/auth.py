import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

import app.routers.depends as deps
from app.core.config import settings
from app.crud import user as crud_user

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
    print(
        "🍓   Secret key %s" % ("*" * len(settings.secret_key))
        if settings.secret_key
        else "🍓   Secret key: unset"
    )
    print("🍓  Server mode: %s" % settings.flux_server_mode)
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


def check_auth(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(deps.get_db),
):
    """
    Check base64 encoded auth (this is HTTP Basic auth.)
    """
    user = crud_user.authenticate(
        db, user_name=credentials.username, password=credentials.password
    )
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    elif not crud_user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return credentials.username


async def get_basic_header(authentication):
    if not authentication:
        raise HTTPException(status_code=400, detail="Authentication header invalid")
