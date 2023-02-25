import flux.job
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import app.library.flux as flux_cli
import app.library.helpers as helpers
import app.library.launcher as launcher
from app.core.config import settings
from app.forms import SubmitForm
from app.library.auth import check_auth

# These views never have auth!
router = APIRouter(tags=["views"])

# These views do :)
auth_views_router = APIRouter(
    tags=["auth-views"],
    dependencies=[Depends(check_auth)] if settings.require_auth else [],
    responses={404: {"description": "Not found"}},
)
templates = Jinja2Templates(directory="templates/")

# Require auth (and the user in the view)
user_auth = Depends(check_auth) if settings.require_auth else None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page to show welcome, etc.
    """
    data = helpers.get_page("index.md")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data,
        },
    )


# List jobs
@auth_views_router.get("/jobs", response_class=HTMLResponse)
async def jobs_table(request: Request, user=user_auth):
    jobs = list(flux_cli.list_jobs_detailed(user=user).values())
    return templates.TemplateResponse(
        "jobs/jobs.html",
        {
            "request": request,
            "jobs": jobs,
        },
    )


# View job detail (and log)
@auth_views_router.get(
    "/job/{jobid}",
    response_class=HTMLResponse,
    name="job_info",
    operation_id="job_info",
)
async def job_info(request: Request, jobid, msg=None, user=user_auth):
    job = flux_cli.get_job(jobid, user=user)

    # If we have a message, add to messages
    messages = [msg] if msg else []

    # If not completed, ask info to return after a second of waiting
    if job["state"] == "INACTIVE":
        info = flux_cli.get_job_output(jobid, user=user)

    # Otherwise ensure we get all the logs!
    else:
        info = flux_cli.get_job_output(jobid, user=user, delay=1)
    return templates.TemplateResponse(
        "jobs/job.html",
        {
            "title": f"Job {jobid}",
            "messages": messages,
            "request": request,
            "job": job,
            "info": info,
        },
    )


# Submit a job via a form
@auth_views_router.get("/jobs/submit", response_class=HTMLResponse)
async def submit_job(request: Request, _=user_auth):
    form = SubmitForm(request)
    return templates.TemplateResponse(
        "jobs/submit.html",
        {"request": request, "has_gpus": settings.has_gpus, "form": form},
    )


# Button to cancel a job
@auth_views_router.get("/job/{jobid}/cancel", response_class=HTMLResponse)
async def cancel_job(request: Request, jobid, user=user_auth):
    from app.main import app

    message, _ = flux_cli.cancel_job(jobid, user=user)
    url = app.url_path_for(name="job_info", jobid=jobid) + "?msg=" + message
    return RedirectResponse(url=url)


@auth_views_router.post("/jobs/submit")
async def submit_job_post(request: Request, user=user_auth):
    """
    Receive data posted (submit) to the form.
    """
    print(user)
    from app.main import app

    messages = []
    form = SubmitForm(request)
    await form.load_data()
    if form.is_valid():
        print("🍦 Submit form is valid!")
        print(form.kwargs)

        if form.kwargs.get("is_launcher") is True:
            messages.append(launcher.launch(form.kwargs, workdir=form.workdir))
        else:
            return submit_job_helper(request, app, form, user=user)
    else:
        print("🍒 Submit form is NOT valid!")
    return templates.TemplateResponse(
        "jobs/submit.html",
        context={
            "request": request,
            "form": form,
            "messages": messages,
            "has_gpus": settings.has_gpus,
            **form.__dict__,
        },
    )


def submit_job_helper(request, app, form, user):
    """
    A helper to submit a flux job (not a launcher)
    """
    # Submit the job and return the ID, but allow for error
    if 1 == 1:
        # Prepare the flux job! We don't support envars here yet
        fluxjob = flux_cli.prepare_job(
            form.kwargs, runtime=form.runtime, workdir=form.workdir
        )
        flux_future = flux_cli.submit_job(app.handle, fluxjob, user=user)
        jobid = flux_future.get_id()
        intid = flux.job.JobID(jobid)
        message = f"Your job was successfully submit! 🦊 <a target='_blank' style='color:magenta' href='/job/{intid}'>{jobid}</a>"
        return templates.TemplateResponse(
            "jobs/submit.html",
            context={
                "request": request,
                "form": form,
                "messages": [message],
            },
        )
    # except Exception as e:
    #    form.errors.append("There was an issue submitting that job: %s" % str(e))

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
    data = helpers.get_page(page_name + ".md")
    return templates.TemplateResponse("page.html", {"request": request, "data": data})
