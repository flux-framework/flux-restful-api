import json
import logging
import threading
import time
import urllib.request
from typing import Optional

from jose import jwt
from sqlalchemy.orm import Session

from app.auth.base import AuthBackend, AuthError, Principal, is_admin, is_system_user
from app.core.config import settings

logger = logging.getLogger("flux-restful")

ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]

# Minimum time between JWKS refreshes triggered by an unknown key id, so that
# unauthenticated requests cannot make the server hammer the provider.
JWKS_REFRESH_MIN_SECONDS = 60


class OidcBackend(AuthBackend):
    """
    Accept tokens issued by an OpenID Connect / OAuth2 provider.

    Clients obtain a token from the provider themselves and present it as a
    bearer token. The server verifies the signature against the provider's
    JWKS, plus the issuer (FLUX_OIDC_ISSUER) and audience (FLUX_OIDC_AUDIENCE,
    normally the client id). The username is the "sub" claim by default: it is
    the only claim OIDC guarantees to be stable and unique for an issuer, and
    claims like preferred_username or email may be user-chosen. Superusers are
    the usernames (claim values) in FLUX_ADMIN_USERS.

    FLUX_OIDC_USERNAME_CLAIM selects another claim. In multi-user mode, where
    the username is the system account jobs run as, it must be set explicitly
    and the value must be an existing account.

    The server never issues tokens for this backend and password login is not
    available.
    """

    name = "oidc"
    supports_password = False
    issues_tokens = False

    def __init__(self, jwks_loader=None):
        # Callable returning a JWK set dict. Injectable for tests.
        self._jwks_loader = jwks_loader or self._fetch_jwks
        self._jwks = None
        self._last_refresh = 0.0
        # Requests are verified from a thread pool, so loads are serialized
        self._lock = threading.Lock()

    @property
    def username_claim(self) -> str:
        return settings.oidc_username_claim or "sub"

    @property
    def multi_user(self) -> bool:
        return settings.flux_server_mode == "multi-user"

    def validate(self) -> None:
        if not settings.oidc_issuer or not settings.oidc_audience:
            raise AuthError(
                "The oidc auth backend requires FLUX_OIDC_ISSUER and FLUX_OIDC_AUDIENCE."
            )
        if self.multi_user and not settings.oidc_username_claim:
            raise AuthError(
                "In multi-user mode jobs run as the authenticated user, so the oidc "
                "backend needs FLUX_OIDC_USERNAME_CLAIM set to a claim that maps "
                "identities to system accounts."
            )

    # JWKS retrieval

    @staticmethod
    def _get_json(url: str) -> dict:
        if not url.startswith("https://"):
            raise AuthError(f"OIDC endpoints must use https, got {url}")
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.load(response)

    def _fetch_jwks(self) -> dict:
        url = settings.oidc_jwks_url
        if not url:
            discovery = (
                settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration"
            )
            url = self._get_json(discovery)["jwks_uri"]
        return self._get_json(url)

    def jwks(self, refresh: bool = False) -> dict:
        if self._jwks is None or refresh:
            with self._lock:
                if self._jwks is None or refresh:
                    self._jwks = self._jwks_loader()
                    self._last_refresh = time.monotonic()
        return self._jwks

    def _maybe_refresh(self, kid: Optional[str]) -> None:
        """
        Refresh keys for an unknown key id (rotation), at most once per
        JWKS_REFRESH_MIN_SECONDS, so junk tokens cannot trigger fetches.

        The slot is claimed under the lock before fetching, so concurrent
        requests that arrive during a fetch do not each start their own.
        """
        if not kid or self._has_key(kid):
            return
        with self._lock:
            if time.monotonic() - self._last_refresh < JWKS_REFRESH_MIN_SECONDS:
                return
            self._last_refresh = time.monotonic()
        self.jwks(refresh=True)

    def _has_key(self, kid: Optional[str]) -> bool:
        return any(key.get("kid") == kid for key in self.jwks().get("keys", []))

    # Backend interface

    def issue_token(self, principal: Principal) -> str:
        raise AuthError(
            "Tokens for the oidc backend are issued by the identity provider."
        )

    def verify_token(self, db: Session, token: str) -> Optional[Principal]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.JWTError:
            return None

        try:
            self._maybe_refresh(header.get("kid"))
            claims = jwt.decode(
                token,
                self.jwks(),
                algorithms=ALGORITHMS,
                audience=settings.oidc_audience,
                issuer=settings.oidc_issuer,
                options={"verify_at_hash": False},
            )
        except (jwt.JWTError, AuthError, OSError) as e:
            logger.debug("OIDC token rejected: %s", e)
            return None

        username = claims.get(self.username_claim)
        if not username or not isinstance(username, str):
            return None
        if self.multi_user:
            # The username is the account jobs run as: it must exist and
            # must not be a privileged account (see FLUX_MIN_UID)
            if not is_system_user(username):
                logger.warning(
                    "OIDC user %s is not an allowed system account", username
                )
                return None
        return Principal(
            user_name=username, is_superuser=is_admin(username), backend=self.name
        )
