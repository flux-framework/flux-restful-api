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

    flux.job.cancel(app.handle, jobid)
    return JSONResponse(
        content={"Message": "Job is requested to cancel."}, status_code=200
    )


@router.post("/jobs/submit")
async def submit_job(request: Request):
    """
    Submit a job to our running cluster.
    """
    from app.main import app

    payload = await request.json()
    if "command" not in payload or not payload["command"]:
        return JSONResponse(
            content={"Message": "'command' is required."}, status_code=400
        )

    # Generate the flux job
    command = shlex.split(payload["command"])
    fluxjob = JobspecV1.from_command(command=command)

    # A duration of zero (the default) means unlimited
    fluxjob.duration = payload.get("runtime", 0) or 0

    # Ensure the cwd is the snakemake working directory
    # TODO user should be able to provide envars in payload
    fluxjob.environment = dict(os.environ)
    flux_future = flux.job.submit_async(app.handle, fluxjob)
    jobid = flux_future.get_id()

    # TODO we should write jobid and other metadata to database?
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
