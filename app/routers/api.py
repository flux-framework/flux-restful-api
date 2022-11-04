import os
import shlex

import flux.job
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from flux.job import JobspecV1

from app.core.config import settings
from app.library.auth import get_basic_header

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_basic_header)] if settings.flux_require_auth else [],
    responses={404: {"description": "Not found"}},
)
templates = Jinja2Templates(directory="templates/")


@router.get("/")
async def list_jobs():
    print('TODO VANESSA IMPLEMENT MEEEE')

@router.get("/submit")
async def submit_job(request: Request):
    from app.main import app
    payload = await request.json()
    if "command" not in payload or not payload['command']:    
        return JSONResponse(content={"Message": "'command' is required."}, status_code=400)

    # Generate the flux job
    command = shlex.split(payload['command'])
    fluxjob = JobspecV1.from_command(command=command)

    # A duration of zero (the default) means unlimited
    fluxjob.duration = payload.get('runtime', 0) or 0

    # Ensure the cwd is the snakemake working directory
    # TODO user should be able to provide envars in payload
    fluxjob.environment = dict(os.environ)
    flux_future = flux.job.submit_async(app.handle, fluxjob)
    jobid = flux_future.get_id()

    # TODO we should write jobid and other metadata to database?
    result = jsonable_encoder({"Message": "Job submit.", "id": jobid})
    return JSONResponse(content=result, status_code=200)


@router.get("/{id}")
async def get_job(id: str):
    print('TODO VANESSA IMPLEMENT MEEEE')
    print(id)