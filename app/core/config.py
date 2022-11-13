import os

from pydantic import BaseSettings


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
    Get a boolean from the environment, meaning the value is set.
    """
    return default if not os.environ.get(key) else not default


class Settings(BaseSettings):
    """
    Basic settings and defaults for the Flux RESTFul API
    """

    app_name: str = "Flux RESTFul API"

    # These map to envars, e.g., FLUX_USER
    has_gpus: bool = get_bool_envar("FLUX_HAS_GPUS")

    # Assume there is at least one node!
    flux_nodes: int = get_int_envar("FLUX_NUMBER_NODES", 1)

    flux_user: str = os.environ.get("FLUX_USER")
    flux_token: str = os.environ.get("FLUX_TOKEN")
    require_auth: bool = get_bool_envar("FLUX_REQUIRE_AUTH")


settings = Settings()
