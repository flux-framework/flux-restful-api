import os

import flux.job
import flux.resource
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

import app.library.flux as flux_cli
import app.library.helpers as helpers
from app.core.config import settings
from app.library.auth import alert_auth, check_auth

# Print (hidden message) to give status of auth
alert_auth()
router = APIRouter(
    prefix="/v1",
    tags=["jobs"],
    dependencies=[Depends(check_auth)] if settings.require_auth else [],
    responses={404: {"description": "Not found"}},
)
templates = Jinja2Templates(directory="templates/")


@router.post("/service/stop")
async def service_stop():
    """
    Raise an error to stop (kill) the service.

    We need a good way to deal this - ideally we can pass a flux start PID?
    """
    print("Goodbye my friends! It was a pleasure, see you next time! 👋")
    os.system("flux shutdown")


@router.get("/jobs")
async def list_jobs(request: Request):
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

        jobs = flux_cli.list_jobs_detailed(limit)
        if helpers.has_boolean_arg(payload, "listing"):
            jobs = list(jobs.values())
    else:
        listing = flux_cli.list_jobs()
        jobs = jsonable_encoder({"jobs": listing.get_jobs()})
    return JSONResponse(content=jobs, status_code=200)


@router.get("/nodes")
async def list_nodes():
    """
    List nodes known to the Flux handle.
    """
    from app.main import app

    rpc = flux.resource.list.resource_list(app.handle)
    listing = rpc.get()
    nodes = jsonable_encoder(
        {"nodes": list({str(node) for node in listing.free.nodelist})}
    )
    return JSONResponse(content=nodes, status_code=200)


@router.post("/jobs/{jobid}/cancel")
async def cancel_job(jobid):
    """
    Cancel a running flux job
    """
    from app.main import app

    try:
        flux.job.cancel(app.handle, jobid)
    # This is usually FileNotFoundError
    except Exception as e:
        return JSONResponse(
            content={"Message": "Job cannot be cancelled: %s." % e}, status_code=400
        )

    return JSONResponse(
        content={"Message": "Job is requested to cancel."}, status_code=200
    )


@router.post("/jobs/submit")
async def submit_job(request: Request):
    """
    Submit a job to our running cluster.

    The logic for parsing a submission is only required here, so we
    include everything in this function instead of having separate
    functions.
    """
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
    for optional in [
        "num_tasks",
        "cores_per_task",
        "gpus_per_task",
        "num_nodes",
        "exclusive",
    ]:
        if optional in payload and payload[optional]:
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

    # Prepare the flux job!
    fluxjob = flux_cli.prepare_job(
        kwargs, runtime=runtime, workdir=workdir, envars=envars
    )

    # Submit the job and return the ID, but allow for error
    try:
        flux_future = flux.job.submit_async(app.handle, fluxjob)
    except Exception as e:
        result = jsonable_encoder(
            {"Message": "There was an issue submitting that job.", "Error": str(e)}
        )
        return JSONResponse(content=result, status_code=400)

    jobid = flux_future.get_id()
    result = jsonable_encoder({"Message": "Job submit.", "id": jobid})
    return JSONResponse(content=result, status_code=200)


@router.get("/jobs/{jobid}")
async def get_job(jobid):
    """
    Get job info based on id.
    """
    info = flux_cli.get_job(jobid)
    info = jsonable_encoder(info)
    return JSONResponse(content=info, status_code=200)


@router.get("/jobs/{jobid}/output")
async def get_job_output(jobid):
    """
    Get job output based on id.
    """
    lines = []
    from app.main import app

    # If the submit is too close to the log reqest, it cannot find the file handle
    # It could be also the jobid cannot be found.
    try:
        for line in flux.job.event_watch(app.handle, jobid, "guest.output"):
            if "data" in line.context:
                lines.append(line.context["data"])
        output = jsonable_encoder({"Output": lines})
        return JSONResponse(content=output, status_code=200)

    except Exception:
        pass
    info = jsonable_encoder(
        {"Message": "The output does not exist yet, or the jobid is incorrect."}
    )
    return JSONResponse(content=info, status_code=200)
