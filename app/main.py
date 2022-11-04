import logging
import os
import sys

from fastapi import FastAPI, Request, Depends 
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.logging import init_loggers
from app.routers import api, views

from .library.helpers import openfile

init_loggers()
log = logging.getLogger("flux-restful")

app = FastAPI()

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

app.include_router(views.router)
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
    except:
        sys.exit(
            "Cannot find flux instance! Ensure you have run flux start or similar."
        )
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    data = openfile("index.md")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data,
        },
    )


@app.get("/page/{page_name}", response_class=HTMLResponse)
async def show_page(request: Request, page_name: str):
    data = openfile(page_name + ".md")
    return templates.TemplateResponse("page.html", {"request": request, "data": data})
