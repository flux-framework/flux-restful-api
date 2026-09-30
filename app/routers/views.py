import os
from urllib.parse import urlencode

import flux.job
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

import app.library.flux as flux_cli
import app.library.helpers as helpers
import app.library.launcher as launcher
import app.routers.depends as deps
from app.core.config import settings
from app.forms import SubmitForm
from app.library import csrf

# These views never have auth!
router = APIRouter(tags=["views"])

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(os.path.dirname(here))
templates = Jinja2Templates(directory=os.path.join(root, "templates"))

# These views require an authenticated user, unless the auth backend is "none"
auth_views_router = APIRouter(
    tags=["auth-views"],
    dependencies=[Depends(deps.current_user_views)],
    responses={404: {"description": "Not found"}},
)

# The authenticated user for a view (None when the auth backend is "none")
user_auth = Depends(deps.current_user_views)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page to show welcome, etc.
    """
    data = helpers.get_page("index.md")
    return templates.TemplateResponse(request, "index.html", {"data": data})


# List jobs
@auth_views_router.get("/jobs", response_class=HTMLResponse)
async def jobs_table(request: Request, user=user_auth):
    jobs = list(flux_cli.list_jobs_detailed(user=user).values())
    return templates.TemplateResponse(request, "jobs/jobs.html", {"jobs": jobs})


@router.get("/logout")
async def logout(request: Request, response: Response):
    """
    This isn't entirely working yet.

    I usually open a new tab/window to reset basic auth. We likely
    need a logout button to be handled somehow in javascript.
    """
    response.delete_cookie("basic")
    response.delete_cookie("bearer")
    response.delete_cookie("access_token")
    data = helpers.get_page("index.md")
    return templates.TemplateResponse(request, "index.html", {"data": data})


# View job detail (and log)
@auth_views_router.get(
    "/job/{jobid}",
    response_class=HTMLResponse,
    name="job_info",
    operation_id="job_info",
)
async def job_info(request: Request, jobid, msg=None, user=user_auth):
    job = flux_cli.get_job(jobid, user=user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # If we have a message, add to messages (the template escapes it)
    messages = [msg] if msg else []

    # If not completed, ask info to return after a second of waiting
    if job["state"] == "INACTIVE":
        info = flux_cli.get_job_output(jobid, user=user)

    # Otherwise ensure we get all the logs!
    else:
        info = flux_cli.get_job_output(jobid, user=user, delay=1)
    return templates.TemplateResponse(
        request,
        "jobs/job.html",
        {
            "title": f"Job {jobid}",
            "messages": messages,
            "job": job,
            "info": info,
        },
    )


# Submit a job via a form
@auth_views_router.get("/jobs/submit", response_class=HTMLResponse)
async def submit_job(request: Request, user=user_auth):
    form = SubmitForm(request)
    return templates.TemplateResponse(
        request,
        "jobs/submit.html",
        {"has_gpus": settings.has_gpus, "form": form},
    )


# Button to cancel a job: a POST form with a CSRF token, never a GET link
@auth_views_router.post("/job/{jobid}/cancel", response_class=HTMLResponse)
async def cancel_job(request: Request, jobid, user=user_auth):
    from app.main import app

    await csrf.verify_form(request)
    message, _ = flux_cli.cancel_job(jobid, user=user)
    url = app.url_path_for("job_info", jobid=jobid) + "?" + urlencode({"msg": message})
    return RedirectResponse(url=url, status_code=303)


@auth_views_router.post("/jobs/submit")
async def submit_job_post(request: Request, user=user_auth):
    """
    Receive data posted (submit) to the form.
    """
    messages = []
    form = SubmitForm(request)
    await form.load_data()
    csrf.verify(request, form.csrf_token)
    if form.is_valid():
        if form.kwargs.get("is_launcher") is True:
            messages.append(
                launcher.launch(form.kwargs, workdir=form.workdir, user=user)
            )
        else:
            return submit_job_helper(request, form, user=user)
    return templates.TemplateResponse(
        request,
        "jobs/submit.html",
        context={
            "form": form,
            "messages": messages,
            "has_gpus": settings.has_gpus,
            **form.__dict__,
        },
    )


def submit_job_helper(request, form, user):
    """
    A helper to submit a flux job (not a launcher)
    """
    from app.main import app

    # Submit the job and return the ID, but allow for error
    # Prepare the flux job! We don't support envars here yet
    try:
        fluxjob = flux_cli.prepare_job(
            user, form.kwargs, runtime=form.runtime, workdir=form.workdir
        )
        flux_future = flux_cli.submit_job(app.handle, fluxjob, user=user)
        jobid = flux_future.get_id()
        intid = flux.job.JobID(jobid)
        # Markup.format escapes the values; the template escapes everything else
        message = Markup(
            "Your job was successfully submit! 🦊 "
            "<a target='_blank' style='color:magenta' href='/job/{}'>{}</a>"
        ).format(intid, jobid)
        return templates.TemplateResponse(
            request,
            "jobs/submit.html",
            context={
                "form": form,
                "messages": [message],
            },
        )
    except Exception as e:
        form.errors.append("There was an issue submitting that job: %s" % str(e))

    return templates.TemplateResponse(
        request,
        "jobs/submit.html",
        context={
            "form": form,
            "has_gpus": settings.has_gpus,
            **form.__dict__,
        },
    )


# These are generic informational pages
@auth_views_router.get("/page/{page_name}", response_class=HTMLResponse)
async def show_page(request: Request, page_name: str):
    data = helpers.get_page(page_name + ".md")
    return templates.TemplateResponse(request, "page.html", {"data": data})
