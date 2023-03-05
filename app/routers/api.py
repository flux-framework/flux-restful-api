import asyncio
import os
from datetime import timedelta

import flux.job
import flux.resource
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import app.core.security as security
import app.library.flux as flux_cli
import app.library.helpers as helpers
import app.library.launcher as launcher
import app.models as models
import app.routers.depends as deps
from app.core.config import settings
from app.crud import user as crud_user
from app.library.auth import alert_auth

# Print (hidden message) to give status of auth
alert_auth()
router = APIRouter(prefix="/v1", tags=["jobs"])
no_auth_router = APIRouter(prefix="/v1", tags=["jobs"])


templates = Jinja2Templates(directory="templates/")


@router.post(f"/{deps.login_url}")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(deps.get_db)
):
    """
    This is the API endpoint to request an authentication token.
    """
    user = crud_user.authenticate(
        db, user_name=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not crud_user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.access_token_expires_minutes)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "Bearer",
    }


@router.post("/service/stop")
async def service_stop(user: models.User = Depends(deps.get_current_active_superuser)):
    """
    Raise an error to stop (kill) the service.

    We need a good way to deal this - ideally we can pass a flux start PID?
    """
    print("Goodbye my friends! It was a pleasure, see you next time! 👋")
    os.system("flux shutdown")


@router.get("/jobs/search")
async def jobs_listing(
    request: Request, user: models.User = Depends(deps.get_current_active_user)
):
    """
    Jobslist is intended to be used by the server to render data tables

    Since this is specific to jquery datables, we don't document.
    """
    start = request.query_params.get("start")
    length = request.query_params.get("length")
    draw = request.query_params.get("draw") or 1
    query = request.query_params.get("search[value]") or request.query_params.get(
        "search"
    )

    # If we have a query, filter to those that have in the name
    jobs = list(flux_cli.list_jobs_detailed(user=user).values())
    total = len(jobs)

    # Now filter
    if query:
        jobs = flux_cli.query_jobs(jobs, query)

    # If we are filtering to a range
    if start and int(start) < len(jobs):
        jobs = jobs[int(start) :]

    # Do we have a length?
    if length and int(length) < len(jobs):
        jobs = jobs[0 : int(length)]
    return JSONResponse(
        content={
            "data": jobs,
            "draw": draw,
            "recordsTotal": total,
            "recordsFiltered": len(jobs),
        },
        status_code=200,
    )


@router.get("/jobs")
async def list_jobs(
    request: Request, user: models.User = Depends(deps.get_current_active_user)
):
    """
    List flux jobs associated with the handle.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Does the requester want details - in dict or listing form?
    if helpers.has_boolean_arg(payload, "details"):
        # Job limit (only relevant for details)
        limit = helpers.get_int_arg(payload, "limit")

        jobs = flux_cli.list_jobs_detailed(limit=limit, user=user)
        if helpers.has_boolean_arg(payload, "listing"):
            jobs = list(jobs.values())
    else:
        listing = flux_cli.list_jobs(user=user)
        jobs = jsonable_encoder({"jobs": listing.get_jobs()})
    return JSONResponse(content=jobs, status_code=200)


@router.get("/nodes")
async def list_nodes(user: models.User = Depends(deps.get_current_active_user)):
    """
    List nodes known to the Flux handle.
    """
    from app.main import app

    rpc = flux.resource.list.resource_list(app.handle)
    listing = rpc.get()
    nodes = jsonable_encoder(
        {"nodes": list({str(node) for node in listing.up.nodelist})}
    )
    return JSONResponse(content=nodes, status_code=200)


@router.post("/jobs/{jobid}/cancel")
async def cancel_job(jobid, user: models.User = Depends(deps.get_current_active_user)):
    """
    Cancel a running flux job
    """
    message, return_code = flux_cli.cancel_job(jobid, user)
    return JSONResponse(
        content={"Message": message, "id": jobid}, status_code=return_code
    )


@router.post("/jobs/submit")
async def submit_job(
    request: Request, user: models.User = Depends(deps.get_current_active_user)
):
    """
    Submit a job to our running cluster.

    The logic for parsing a submission is only required here, so we
    include everything in this function instead of having separate
    functions.
    """
    print(f"User for submit is {user}")
    from app.main import app

    # This can bork if no payload is provided
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            content={"Message": "A 'command' is minimally required."}, status_code=400
        )

    kwargs = {}

    # Required arguments
    for required in ["command"]:
        kwargs[required] = payload.get(required)

    # Optional arguments
    as_int = ["num_tasks", "cores_per_task", "gpus_per_task", "num_nodes"]
    as_bool = ["exclusive"]
    as_is = ["option_flags"]

    for optional in as_int + as_bool + as_is:
        if optional in payload and payload[optional]:
            if optional in as_bool:
                kwargs[optional] = bool(payload[optional])
            elif optional in as_int:
                kwargs[optional] = int(payload[optional])
            else:
                kwargs[optional] = payload[optional]

    # One off args not provided to JobspecV1
    envars = payload.get("envars", {})
    workdir = payload.get("workdir")
    runtime = payload.get("runtime", 0) or 0

    # Validate the payload, return meaningful message if something is off
    invalid_messages = flux_cli.validate_submit_kwargs(
        kwargs, envars=envars, runtime=runtime
    )
    if invalid_messages:
        return JSONResponse(
            content={"Message": "Invalid submit request", "Errors": invalid_messages},
            status_code=400,
        )

    # Are we using a launcher instead?
    is_launcher = payload.get("is_launcher", False)
    if is_launcher:
        print("TODO need to test multi-user")
        message = launcher.launch(kwargs, workdir=workdir, envars=envars)
        result = jsonable_encoder({"Message": message, "id": "MANY"})
    else:
        # Prepare and submit the job and return the ID, but allow for error
        try:
            print(f"Preparing flux job with {kwargs}")
            fluxjob = flux_cli.prepare_job(
                user, kwargs, runtime=runtime, workdir=workdir, envars=envars
            )
            print(f"Prepared flux job {fluxjob}")
            # This handles either a single/multi user case
            flux_future = flux_cli.submit_job(app.handle, fluxjob, user=user)
        except Exception as e:
            result = jsonable_encoder(
                {"Message": "There was an issue submitting that job.", "Error": str(e)}
            )
            return JSONResponse(content=result, status_code=400)
        jobid = flux_future.get_id()
        result = jsonable_encoder({"Message": "Job submit.", "id": jobid})

    # If we get down here, either launcher derived or submit
    return JSONResponse(content=result, status_code=200)


@router.get("/jobs/{jobid}")
async def get_job(jobid, user: models.User = Depends(deps.get_current_active_user)):
    """
    Get job info based on id.
    """
    info = flux_cli.get_job(jobid, user=user)
    info = jsonable_encoder(info)
    return JSONResponse(content=info, status_code=200)


@router.get("/jobs/{jobid}/output")
async def get_job_output(
    jobid, user: models.User = Depends(deps.get_current_active_user)
):
    """
    Get job output based on id.
    """
    lines = flux_cli.get_job_output(jobid, user=user)

    # We have output
    if lines:
        output = jsonable_encoder({"Output": lines})
        return JSONResponse(content=output, status_code=200)

    info = jsonable_encoder(
        {"Message": "The output does not exist yet, or the jobid is incorrect."}
    )
    return JSONResponse(content=info, status_code=200)


async def streamer(generator):
    """
    Helper function to stream output lines, break if cancelled.
    """
    try:
        for line in generator:
            yield line
    except asyncio.CancelledError:
        print("caught cancelled error")


@router.get("/jobs/{jobid}/output/stream")
async def get_job_stream_output(jobid):
    """
    Non-blocking variant to stream output until control+c.
    """
    stream = flux_cli.stream_job_output(jobid)
    return StreamingResponse(streamer(stream))
