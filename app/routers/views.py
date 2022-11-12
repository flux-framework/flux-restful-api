import flux
import flux.job
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import app.library.flux as flux_cli
from app.core.config import settings
from app.forms import SubmitForm
from app.library.auth import check_auth
from app.library.helpers import openfile

# These views never have auth!
router = APIRouter(tags=["views"])

# These views do :)
auth_views_router = APIRouter(
    tags=["auth-views"],
    dependencies=[Depends(check_auth)] if settings.require_auth else [],
    responses={404: {"description": "Not found"}},
)
templates = Jinja2Templates(directory="templates/")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page to show welcome, etc.
    """
    data = openfile("index.md")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data,
        },
    )


# List jobs
@auth_views_router.get("/jobs", response_class=HTMLResponse)
async def jobs_table(request: Request, messages=None):
    return templates.TemplateResponse(
        "jobs/jobs.html",
        {
            "request": request,
            "jobs": flux_cli.list_jobs_detailed(),
            "messages": messages or [],
        },
    )


# Submit a job via a form
@auth_views_router.get("/jobs/submit", response_class=HTMLResponse)
async def submit_job(request: Request):
    form = SubmitForm(request)
    return templates.TemplateResponse(
        "jobs/submit.html",
        {"request": request, "has_gpus": settings.has_gpus, "form": form},
    )


@auth_views_router.post("/jobs/submit")
async def submit_job_post(request: Request):
    """
    Receive data posted (submit) to the form.
    """
    from app.main import app

    form = SubmitForm(request)
    await form.load_data()
    if form.is_valid():
        print("🍦 Submit form is valid!")

        # Prepare the flux job! We don't support envars here yet
        fluxjob = flux_cli.prepare_job(
            form.kwargs, runtime=form.runtime, workdir=form.workdir
        )

        # Submit the job and return the ID, but allow for error
        try:
            flux_future = flux.job.submit_async(app.handle, fluxjob)
            jobid = flux_future.get_id()
            return templates.TemplateResponse(
                "jobs/submit.html",
                context={
                    "request": request,
                    "form": form,
                    "messages": [f"Your job was successfully submit! 🦊 {jobid}"],
                },
            )
        except Exception as e:
            form.errors.append("There was an issue submitting that job: %s" % str(e))
    else:
        print("🍒 Submit form is NOT valid!")
    return templates.TemplateResponse(
        "jobs/submit.html",
        context={
            "request": request,
            "form": form,
            "has_gpus": settings.has_gpus,
            **form.__dict__,
        },
    )


# These are generic informational pages
@auth_views_router.get("/page/{page_name}", response_class=HTMLResponse)
async def show_page(request: Request, page_name: str):
    data = openfile(page_name + ".md")
    return templates.TemplateResponse("page.html", {"request": request, "data": data})
