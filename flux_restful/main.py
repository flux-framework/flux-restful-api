import logging
import os
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import flux_restful.auth as auth
import flux_restful.library.flux as flux_cli
from flux_restful.core.config import settings
from flux_restful.core.logging import init_loggers
from flux_restful.db.base import Base
from flux_restful.db.session import engine
from flux_restful.library import csrf
from flux_restful.library import handle as flux_handle
from flux_restful.routers import api, views

init_loggers()
log = logging.getLogger("flux-restful")

# Create (and validate) the auth backend now so misconfiguration fails at
# startup rather than on the first request.
log.info("Authentication: %s", auth.describe())

# Alembic should make the models
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

# Multi-user mode becomes each user to submit their jobs, which only root can do
if settings.require_auth and settings.flux_server_mode == "multi-user":
    if os.getuid() != 0:
        sys.exit(
            "FLUX_SERVER_MODE=multi-user runs jobs as the authenticated user, "
            f"which requires the server to run as root (it is uid {os.getuid()})."
        )

app = FastAPI()


@app.exception_handler(flux_cli.JobAccessDenied)
async def job_access_denied(request: Request, exc: flux_cli.JobAccessDenied):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(flux_cli.InvalidJobId)
async def invalid_job_id(request: Request, exc: flux_cli.InvalidJobId):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(flux_handle.FluxUnavailable)
async def flux_unavailable(request: Request, exc: flux_handle.FluxUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# Templates and static files ship inside the package
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
static_root = os.path.join(here, "static")
template_root = os.path.join(here, "templates")

# Create templates, ensure we can get flashed messages from template session
templates = Jinja2Templates(directory=template_root)

app.mount("/static", StaticFiles(directory=static_root), name="static")

app.middleware("http")(csrf.middleware)

app.include_router(views.router)
app.include_router(views.auth_views_router)
app.include_router(api.router)

# Fail at startup if there is no Flux instance to talk to. Requests use a
# per-thread handle (see flux_restful.library.handle); nothing is created per request.
try:
    log.info("Flux instance size: %s", flux_handle.check_connection())
except flux_handle.FluxUnavailable as e:
    sys.exit(str(e))

# Paths used by templates and helpers
app.here = here
app.root = root
