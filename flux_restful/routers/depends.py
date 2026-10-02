from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from flux_restful.auth import Principal, get_backend
from flux_restful.auth.base import is_system_user
from flux_restful.core.config import settings
from flux_restful.db.session import SessionLocal

login_url = f"{settings.api_version}/login/access-token"

# auto_error is off so the "none" backend can serve anonymous requests and so
# we control the 401 response (clients rely on the WWW-Authenticate header).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=login_url, auto_error=False)
basic_scheme = HTTPBasic(auto_error=False)


def get_db() -> Generator:
    """
    Get the database in a context so we can then close it.
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def unauthorized(detail: str, scheme: str = "Bearer") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": scheme},
    )


def _accept(principal: Optional[Principal]) -> Principal:
    """
    Final checks on an authenticated principal, whatever backend produced it.
    """
    if principal is None:
        raise unauthorized("Could not validate credentials")
    if not principal.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    # In multi-user mode the server becomes this user to run their jobs, so
    # the name must be a real, unprivileged system account (FLUX_MIN_UID).
    # Backends may check earlier for a better message; this is authoritative.
    if settings.flux_server_mode == "multi-user" and not is_system_user(
        principal.user_name
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{principal.user_name} is not an allowed system account on this server.",
        )
    return principal


def _verify(db: Session, token: str) -> Principal:
    return _accept(get_backend().verify_token(db, token))


def current_user(
    db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[Principal]:
    """
    The authenticated API user, or None when the auth backend is "none".
    """
    if get_backend().name == "none":
        return None
    if not token:
        raise unauthorized("Not authenticated")
    return _verify(db, token)


def current_superuser(user: Optional[Principal] = Depends(current_user)) -> Principal:
    """
    The authenticated user, who must be a superuser.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a superuser, but the auth backend is 'none'.",
        )
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return user


def _bearer_token(request: Request) -> Optional[str]:
    """
    A bearer token from the Authorization header or the access_token cookie.

    The cookie is how a browser can use the web UI with backends that have
    no password (oidc). Form posts are protected against cross-site requests
    by flux_restful.library.csrf, so a cookie-authenticated browser cannot be made to
    submit or cancel jobs from another site.
    """
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return request.cookies.get("access_token")


def current_user_views(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPBasicCredentials] = Depends(basic_scheme),
) -> Optional[Principal]:
    """
    The authenticated web UI user, or None when the auth backend is "none".

    A bearer token (header or access_token cookie) is accepted for every
    backend. Password backends additionally accept HTTP Basic auth, which is
    what browsers use.
    """
    backend = get_backend()
    if backend.name == "none":
        return None

    token = _bearer_token(request)
    if token:
        return _verify(db, token)

    if not backend.supports_password:
        raise unauthorized("Not authenticated")
    if credentials is None:
        raise unauthorized("Not authenticated", scheme="Basic")
    principal = backend.authenticate(db, credentials.username, credentials.password)
    if principal is None:
        raise unauthorized("Incorrect user or password", scheme="Basic")
    return _accept(principal)
