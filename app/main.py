import logging
import os
import sys

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.logging import init_loggers
from app.db.base import Base
from app.db.session import engine
from app.routers import api, views

init_loggers()
log = logging.getLogger("flux-restful")

# Alembic should make the models
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

app = FastAPI()

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
static_root = os.path.join(root, "static")
data_root = os.path.join(root, "data")
template_root = os.path.join(root, "templates")

# Create templates, ensure we can get flashed messages from template session
templates = Jinja2Templates(directory=template_root)

app.mount("/static", StaticFiles(directory=static_root), name="static")
app.mount("/data", StaticFiles(directory=data_root), name="data")

app.include_router(views.router)
app.include_router(views.auth_views_router)
app.include_router(api.router)

try:
    import flux
except ImportError:
    sys.exit("Cannot import flux. Make sure flux Python bindings are available.")


@app.middleware("http")
async def load_app_data(request: Request, call_next):
    """
    Middleware to ensure that data is always loaded (do we need?)
    """
    # Save the app root and app directory root (here)
    app.here = here
    app.root = root

    # Use a common flux executor
    try:
        app.handle = flux.Flux()
    except Exception:
        sys.exit(
            "Cannot find flux instance! Ensure you have run flux start or similar."
        )
    return await call_next(request)
