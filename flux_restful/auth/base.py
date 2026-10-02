"""
The authentication backend interface.

A backend answers two questions: "are these credentials valid?" and "who does
this bearer token belong to?" Everything else in the server (routers, the web
views, job submission) only ever sees a Principal, so backends can be swapped
by setting FLUX_AUTH_BACKEND without touching the rest of the code.
"""

import logging
import pwd
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from flux_restful.auth import tokens
from flux_restful.core.config import settings

logger = logging.getLogger("flux-restful")


class AuthError(Exception):
    """A backend is misconfigured or cannot perform the requested operation."""


@dataclass
class Principal:
    """
    An authenticated identity, independent of the backend that produced it.

    user_name is the login name and, in multi-user mode, the system account that
    jobs are submitted as.
    """

    user_name: str
    is_superuser: bool = False
    is_active: bool = True
    backend: str = ""


def is_admin(username: str) -> bool:
    """
    Users listed in FLUX_ADMIN_USERS are superusers regardless of backend.
    """
    return username in settings.admin_users


def is_system_user(username: str) -> bool:
    """
    Whether a name is a system account that a backend may map to.

    Accounts below FLUX_MIN_UID (root, daemons) are never acceptable, so a
    bad claim mapping or a misconfigured PAM stack cannot yield them.
    """
    try:
        record = pwd.getpwnam(username)
    except KeyError:
        return False
    if record.pw_uid < settings.min_uid:
        logger.warning(
            "Refusing system account %s (uid %s below FLUX_MIN_UID=%s)",
            username,
            record.pw_uid,
            settings.min_uid,
        )
        return False
    return True


class AuthBackend:
    """
    Base class for authentication backends.

    Subclasses set ``name`` (the value used in FLUX_AUTH_BACKEND) and override
    ``authenticate`` and/or ``resolve``. Token issuing and verification default
    to server-signed JWTs and only need overriding when tokens come from
    somewhere else (for example an OIDC provider).
    """

    name = "base"

    # Whether authenticate(username, password) is meaningful for this backend.
    # Password backends get HTTP Basic auth for the web views, the OAuth2
    # password form login, and (with FLUX_SECRET_KEY set) the shared-secret
    # token handshake used by the Python client.
    supports_password = False

    # Whether the server issues access tokens for this backend (and therefore
    # needs FLUX_TOKEN_SIGNING_KEY). False when tokens come from elsewhere.
    issues_tokens = True

    def validate(self) -> None:
        """
        Check configuration at startup. Raise AuthError if unusable.
        """

    def authenticate(
        self, db: Session, username: str, password: str
    ) -> Optional[Principal]:
        """
        Validate a username and password. Return a Principal, or None.
        """
        return None

    def resolve(self, db: Session, username: str) -> Optional[Principal]:
        """
        Resolve a username (typically a token subject) to a Principal.

        Return None if the user is unknown or inactive.
        """
        return None

    def issue_token(self, principal: Principal) -> str:
        """
        Issue an access token for an authenticated principal.
        """
        return tokens.create_access_token(principal.user_name, backend=self.name)

    def verify_token(self, db: Session, token: str) -> Optional[Principal]:
        """
        Verify a bearer token and return its Principal, or None if invalid.
        """
        try:
            payload = tokens.decode_access_token(token)
        except tokens.TokenError:
            return None

        # A token issued under a different backend is not valid here, even
        # if the signing key is the same.
        if payload.get("backend") != self.name:
            return None
        subject = payload.get("sub")
        if not subject:
            return None
        return self.resolve(db, subject)
