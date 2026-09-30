"""
Pluggable authentication for the Flux RESTful API.

Select a backend with FLUX_AUTH_BACKEND (see app.core.config.KNOWN_AUTH_BACKENDS).
Routers only depend on get_backend() and the Principal it returns.
"""

from typing import Dict, Optional, Type

from app.auth.base import AuthBackend, AuthError, Principal  # noqa: F401
from app.auth.database import DatabaseBackend, SharedSecretBackend
from app.auth.none import NoAuthBackend
from app.auth.oidc import OidcBackend
from app.auth.pam import PamBackend
from app.core.config import settings

BACKENDS: Dict[str, Type[AuthBackend]] = {
    NoAuthBackend.name: NoAuthBackend,
    DatabaseBackend.name: DatabaseBackend,
    SharedSecretBackend.name: SharedSecretBackend,
    PamBackend.name: PamBackend,
    OidcBackend.name: OidcBackend,
}

_backend: Optional[AuthBackend] = None


def create_backend(name: str) -> AuthBackend:
    """
    Instantiate and validate a backend by name.
    """
    try:
        cls = BACKENDS[name]
    except KeyError:
        raise AuthError(
            f"Unknown auth backend '{name}'. Choose from: {', '.join(BACKENDS)}"
        )
    backend = cls()
    if backend.issues_tokens and not settings.token_signing_key:
        raise AuthError(
            f"The {name} auth backend issues access tokens, so FLUX_TOKEN_SIGNING_KEY "
            "must be set (for example: python3 -c 'import secrets; "
            "print(secrets.token_hex(32))'). It must be the same for every worker."
        )
    backend.validate()
    return backend


def get_backend() -> AuthBackend:
    """
    The configured backend (created on first use).
    """
    global _backend
    if _backend is None:
        _backend = create_backend(settings.auth_backend)
    return _backend


def reset_backend() -> None:
    """
    Forget the cached backend so it is re-created from settings (for tests).
    """
    global _backend
    _backend = None


def handshake_enabled() -> bool:
    """
    The shared-secret handshake on /v1/token needs a password backend and a secret.
    """
    return bool(settings.secret_key) and get_backend().supports_password


def describe() -> dict:
    """
    Public description of how to authenticate, safe to show to anyone.
    """
    backend = get_backend()
    info = {
        "backend": backend.name,
        "password_login": backend.supports_password,
        "shared_secret_handshake": handshake_enabled(),
    }
    if backend.name == OidcBackend.name:
        info["oidc"] = {
            "issuer": settings.oidc_issuer,
            "audience": settings.oidc_audience,
        }
    return info
