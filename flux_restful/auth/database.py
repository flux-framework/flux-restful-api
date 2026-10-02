from typing import Optional

from sqlalchemy.orm import Session

from flux_restful.auth.base import AuthBackend, AuthError, Principal, is_admin
from flux_restful.core.config import settings
from flux_restful.crud import user as crud_user
from flux_restful.models.user import User


class DatabaseBackend(AuthBackend):
    """
    Users and bcrypt password hashes stored in the server database.

    Accounts are managed with ``flux-restful`` (init, add-user).
    """

    name = "database"
    supports_password = True

    def _principal(self, user: User) -> Principal:
        return Principal(
            user_name=user.user_name,
            is_superuser=bool(user.is_superuser) or is_admin(user.user_name),
            is_active=bool(user.is_active),
            backend=self.name,
        )

    def authenticate(
        self, db: Session, username: str, password: str
    ) -> Optional[Principal]:
        if not username or not password:
            return None
        user = crud_user.authenticate(db, user_name=username, password=password)
        if not user or not user.is_active:
            return None
        return self._principal(user)

    def resolve(self, db: Session, username: str) -> Optional[Principal]:
        user = crud_user.get_by_username(db, user_name=username)
        if not user or not user.is_active:
            return None
        return self._principal(user)


class SharedSecretBackend(DatabaseBackend):
    """
    Database users plus the shared-secret token handshake.

    This is what FLUX_REQUIRE_AUTH=true historically meant, and what the
    Python client and the Flux Operator use: the client encodes its username
    and password with FLUX_SECRET_KEY and posts it to /v1/token to obtain an
    access token. The shared secret is only ever used to decode that
    handshake; access tokens are signed with the server-only signing key.
    """

    name = "shared-secret"

    def validate(self) -> None:
        if not settings.secret_key:
            raise AuthError(
                "The shared-secret auth backend requires FLUX_SECRET_KEY to be set."
            )
