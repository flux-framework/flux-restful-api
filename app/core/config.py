import logging
import os
import re
import shlex

from pydantic import BaseSettings

logger = logging.getLogger(__name__)


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


class Settings(BaseSettings):
    """
    Basic settings and defaults for the Flux RESTFul API
    """

    app_name: str = "Flux RESTFul API"

    # These map to envars, e.g., FLUX_USER
    has_gpus: bool = get_bool_envar("FLUX_HAS_GPUS")
    enable_pam: bool = get_bool_envar("FLUX_ENABLE_PAM")

    # Assume there is at least one node!
    flux_nodes: int = get_int_envar("FLUX_NUMBER_NODES", 1)

    flux_user: str = os.environ.get("FLUX_USER")
    flux_token: str = os.environ.get("FLUX_TOKEN")
    require_auth: bool = get_bool_envar("FLUX_REQUIRE_AUTH")

    # Default server option flags
    option_flags: dict = get_option_flags("FLUX_OPTION_FLAGS")

    # If the user requests a launcher, be strict.
    # We only allow nextflow and snakemake, sorry
    known_launchers: list = ["nextflow", "snakemake"]


settings = Settings()
