import logging
import os
import re
import secrets
import shlex
import string
from typing import List, Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

TRUE_VALUES = ("1", "true", "yes", "on")

# Authentication backends known to the server (implemented in app/auth)
KNOWN_AUTH_BACKENDS = ["none", "database", "shared-secret", "pam", "oidc"]


def get_int_envar(key, default=None):
    """
    Get (and parse) an integer environment variable
    """
    value = os.environ.get(key)
    if not value:
        value = default
    try:
        value = int(value)
        return value
    except Exception:
        return default


def get_bool_envar(key, default=False):
    """
    Get a boolean environment variable. Accepts 1/0, true/false, yes/no, on/off.

    An unset or empty variable returns the default.
    """
    value = os.environ.get(key)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in TRUE_VALUES


def get_list_envar(key) -> List[str]:
    """
    Get a comma separated list from the environment.
    """
    value = os.environ.get(key) or ""
    return [item.strip() for item in value.split(",") if item.strip()]


def get_auth_backend() -> str:
    """
    Determine the auth backend from FLUX_AUTH_BACKEND.

    FLUX_REQUIRE_AUTH predates FLUX_AUTH_BACKEND: it meant database users plus
    the shared-secret token handshake, so it maps to "shared-secret".
    """
    backend = (os.environ.get("FLUX_AUTH_BACKEND") or "").strip().lower()
    if not backend:
        backend = "shared-secret" if get_bool_envar("FLUX_REQUIRE_AUTH") else "none"
    if backend not in KNOWN_AUTH_BACKENDS:
        raise ValueError(
            f"FLUX_AUTH_BACKEND must be one of {', '.join(KNOWN_AUTH_BACKENDS)}, "
            f"got '{backend}'"
        )
    return backend


def get_option_flags(key, prefix="-o"):
    """
    Wrapper around parse_option_flags to get from environment.

    The function can then be shared to parse flags from the UI
    in the same way.
    """
    flags = os.environ.get(key) or {}
    if not flags:
        return flags
    return parse_option_flags(flags, prefix)


def parse_option_flags(flags, prefix="-o"):
    """
    Parse key value pairs (optionally with a prefix) from the environment.
    """
    values = {}
    for flag in shlex.split(flags):
        if "=" not in flag:
            logger.warning(f"Missing '=' in flag {flag}, cannot parse.")
            continue
        option, value = flag.split("=", 1)
        if option.startswith(prefix):
            option = re.sub(f"^{prefix}", "", option)
        values[option] = value
    return values


def generate_secret_key(length=32):
    """
    Generate a random key, if one is not provided.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(length))


class Settings(BaseSettings):
    """
    Basic settings and defaults for the Flux RESTFul API
    """

    app_name: str = "Flux RESTFul API"
    api_version: str = "v1"

    # These map to envars, e.g., FLUX_USER
    has_gpus: bool = get_bool_envar("FLUX_HAS_GPUS")

    # Assume there is at least one node!
    flux_nodes: int = get_int_envar("FLUX_NUMBER_NODES", 1)

    # Authentication. See app/auth for the backends.
    auth_backend: str = get_auth_backend()
    require_auth: bool = auth_backend != "none"

    # Usernames that are superusers regardless of backend (comma separated)
    admin_users: List[str] = get_list_envar("FLUX_ADMIN_USERS")

    # Shared with clients so they can encode the /v1/token handshake payload.
    # It is never used to sign access tokens.
    secret_key: Optional[str] = os.environ.get("FLUX_SECRET_KEY")

    # Server-only key that signs access tokens. Required by every backend that
    # issues tokens, so that all workers sign with the same key (see
    # entrypoint.sh, which generates one per container start if unset).
    token_signing_key: Optional[str] = os.environ.get("FLUX_TOKEN_SIGNING_KEY")

    # Lowest uid that may be mapped to a system account by a backend (pam, or
    # oidc in multi-user mode). Keeps root and daemon accounts out of reach
    # of a bad claim mapping.
    min_uid: int = get_int_envar("FLUX_MIN_UID", 1000)

    # pam backend
    pam_service: str = os.environ.get("FLUX_PAM_SERVICE") or "login"

    # oidc backend
    oidc_issuer: Optional[str] = os.environ.get("FLUX_OIDC_ISSUER")
    oidc_audience: Optional[str] = os.environ.get("FLUX_OIDC_AUDIENCE")
    oidc_jwks_url: Optional[str] = os.environ.get("FLUX_OIDC_JWKS_URL")
    # Claim used as the username. Defaults to "sub", the only claim OIDC
    # guarantees to be stable and unique for an issuer.
    oidc_username_claim: Optional[str] = os.environ.get("FLUX_OIDC_USERNAME_CLAIM")

    # If you change this, also change in alembic.ini
    db_file: str = "sqlite:///./flux-restful.db"
    flux_user: str = os.environ.get("FLUX_USER") or "fluxuser"
    flux_token: Optional[str] = os.environ.get("FLUX_TOKEN")
    flux_server_mode: Optional[str] = (
        os.environ.get("FLUX_SERVER_MODE") or "single-user"
    )

    # Validate the server mode provided.
    if flux_server_mode not in ["single-user", "multi-user"]:
        raise ValueError("FLUX_SERVER_MODE must be single-user or multi-user")

    # Expires in 10 hours
    access_token_expires_minutes: int = get_int_envar(
        "FLUX_ACCESS_TOKEN_EXPIRES_MINUTES", 600
    )

    # Default server option flags
    option_flags: dict = get_option_flags("FLUX_OPTION_FLAGS")

    # If the user requests a launcher, be strict.
    # We only allow nextflow and snakemake, sorry
    known_launchers: list = ["nextflow", "snakemake"]


settings = Settings()
