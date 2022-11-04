from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Flux RESTFul API"

    # These map to envars, e.g., FLUX_USER
    flux_user: str = None
    flux_token: str = None
    flux_require_auth: bool = False

settings = Settings()