import os

from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Flux RESTFul API"

    # These map to envars, e.g., FLUX_USER
    flux_user: str = os.environ.get("FLUX_USER")
    flux_token: str = os.environ.get("FLUX_TOKEN")
    flux_require_auth: bool = (
        False if os.environ.get("FLUX_REQUIRE_AUTH") is None else True
    )


settings = Settings()
