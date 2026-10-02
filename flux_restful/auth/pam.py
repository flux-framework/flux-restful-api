import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from flux_restful.auth.base import (
    AuthBackend,
    AuthError,
    Principal,
    is_admin,
    is_system_user,
)
from flux_restful.core.config import settings

logger = logging.getLogger("flux-restful")


class PamBackend(AuthBackend):
    """
    Authenticate against the host's PAM stack (system accounts).

    Requires the ``python-pam`` package. The PAM service is FLUX_PAM_SERVICE
    (default "login"). Superusers are the accounts in FLUX_ADMIN_USERS. This
    pairs naturally with multi-user mode, where jobs run as the system user.
    """

    name = "pam"
    supports_password = True

    def __init__(self, authenticator=None):
        # An object with authenticate(username, password, service=...) -> bool.
        # Injectable so the backend can be tested without PAM.
        self._authenticator = authenticator

    def validate(self) -> None:
        # Fail at startup, not at the first login, if python-pam is missing.
        self._get_authenticator()
        if os.getuid() != 0:
            logger.warning(
                "The pam auth backend can only verify other users' passwords when "
                "the server runs as root (it is running as uid %s); only the server "
                "user's own password will work.",
                os.getuid(),
            )

    def _get_authenticator(self):
        if self._authenticator is None:
            try:
                import pam
            except ImportError as e:
                raise AuthError(
                    "The pam auth backend requires the python-pam package."
                ) from e
            self._authenticator = pam.pam()
        return self._authenticator

    def authenticate(
        self, db: Session, username: str, password: str
    ) -> Optional[Principal]:
        if not username or not password:
            return None
        try:
            ok = self._get_authenticator().authenticate(
                username, password, service=settings.pam_service
            )
        except Exception as e:
            logger.warning("PAM authentication error for %s: %s", username, e)
            ok = False
        if not ok:
            return None
        return self.resolve(db, username)

    def resolve(self, db: Session, username: str) -> Optional[Principal]:
        # Only real, unprivileged system accounts can be principals
        if not is_system_user(username):
            return None
        return Principal(
            user_name=username, is_superuser=is_admin(username), backend=self.name
        )
