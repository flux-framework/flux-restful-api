import json
import os
import shlex

import flux.job
import flux.resource
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from flux.job import JobspecV1

from app.core.config import settings
from app.library.auth import alert_auth, check_auth

# Print (hidden message) to give status of auth
alert_auth()
router = APIRouter(
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
async def list_jobs():
    """
    List flux jobs associated with the handle.
    """
    from app.main import app

    listing = flux.job.job_list(app.handle)
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

    payload = await request.json()
    if "command" not in payload or not payload["command"]:
        return JSONResponse(
            content={"Message": "'command' is required."}, status_code=400
        )

    # Generate the flux job
    command = payload["command"]
    if isinstance(command, str):
        command = shlex.split(command)

    # Optional defaults
    kwargs = {"command": command}
    for optional in [
        "num_tasks",
        "cores_per_task",
        "gpus_per_task",
        "num_nodes",
        "exclusive",
    ]:
        if optional in payload and payload[optional]:
            kwargs[optional] = payload[optional]
    fluxjob = JobspecV1.from_command(**kwargs)

    # Does the user want a working directory?
    workdir = payload.get("workdir")
    if workdir is not None:
        fluxjob.workdir = workdir

    # A duration of zero (the default) means unlimited
    fluxjob.duration = payload.get("runtime", 0) or 0

    # Additional envars in the payload?
    environment = dict(os.environ)
    extra_envars = payload.get("envars", {})
    environment.update(extra_envars)
    fluxjob.environment = environment

    # Submit the job and return the ID, but allow for error
    try:
        flux_future = flux.job.submit_async(app.handle, fluxjob)
    except Exception as e:
        result = jsonable_encoder(
            {"Message": "There was an issue submitting that job.", "Error": str(e)}
        )
        return JSONResponse(content=result, status_code=400)

    jobid = flux_future.get_id()

    # TODO should we write jobid and other metadata to a database?
    result = jsonable_encoder({"Message": "Job submit.", "id": jobid})
    return JSONResponse(content=result, status_code=200)


@router.get("/jobs/{jobid}")
async def get_job(jobid):
    """
    Get job info based on id.
    """
    from app.main import app

    info = flux.job.job_list_id(app.handle, jobid, attrs=["all"])
    info = jsonable_encoder(json.loads(info.get_str()))
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
