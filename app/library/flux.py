import json
import os
import shlex

import flux
import flux.job

from app.core.config import settings


def validate_submit_kwargs(kwargs, envars=None, runtime=None):
    """
    Shared function to validate submit, from API or web UI.

    Kwargs are expected to be given to JobspecV1, and
    everything else is added to the fluxjob.
    """
    errors = []
    if "command" not in kwargs or not kwargs["command"]:
        errors.append("'command' is required.")

    # We can't ask for more nodes than available!
    num_nodes = kwargs.get("num_nodes")
    if num_nodes and num_nodes > settings.flux_nodes:
        errors.append(
            f"The server only has {settings.flux_nodes} nodes, you requested {num_nodes}"
        )

    # If the user asks for gpus and we don't have any, no go
    if "gpus_per_task" in kwargs and not settings.has_gpus:
        errors.append("This server does not support gpus: gpus_per_task cannot be set.")

    # Minimum value of zero
    if runtime and runtime < 0:
        errors.append(f"Runtime must be >= 0, found {runtime}")

    # Minimum values of 1
    for key in ["cpus_per_task", "gpus_per_task"]:
        if key in kwargs and kwargs[key] < 1:
            errors.append(f"Parameter {key} must be >= 1")

    if envars and not isinstance(envars, dict):
        errors.append("Environment variables must be key/value pairs (dict)")
    return errors


def prepare_job(kwargs, runtime=0, workdir=None, envars=None):
    """
    After validation, prepare the job (shared function).
    """
    envars = envars or {}

    # Generate the flux job
    command = kwargs["command"]
    if isinstance(command, str):
        command = shlex.split(command)

    # Delete command from the kwargs (we added because is required and validated that way)
    del kwargs["command"]
    fluxjob = flux.job.JobspecV1.from_command(command, **kwargs)

    if workdir is not None:
        fluxjob.workdir = workdir

    # A duration of zero (the default) means unlimited
    fluxjob.duration = runtime

    # Additional envars in the payload?
    environment = dict(os.environ)
    environment.update(envars)
    fluxjob.environment = environment
    return fluxjob


def list_jobs_detailed(limit=None):
    """
    Get a detailed listing of jobs.
    """
    listing = list_jobs()
    ids = listing.get()["jobs"]
    jobs = {}
    for job in ids:

        # Stop if a limit is defined and we have hit it!
        if limit is not None and len(jobs) >= limit:
            break
        try:
            jobs[job["id"]] = get_job(job["id"])
        except Exception:
            pass
    return jobs


def list_jobs():
    """
    Get a simple listing of jobs (just the ids)
    """
    from app.main import app

    return flux.job.job_list(app.handle)


def get_simple_job(jobid):
    """
    Not used - an original (simpler) implementation.
    """
    from app.main import app

    info = flux.job.job_list_id(app.handle, jobid, attrs=["all"])
    return json.loads(info.get_str())["job"]


def get_job(jobid):
    """
    Get details for a job
    """
    from app.main import app

    payload = {"id": int(jobid), "attrs": ["all"]}
    rpc = flux.job.list.JobListIdRPC(app.handle, "job-list.list-id", payload)
    try:
        jobinfo = rpc.get()["job"]

        # User friendly string from integer
        state = jobinfo["state"]
        jobinfo["state"] = flux.job.info.statetostr(state)

        # Get job info to add to result
        info = rpc.get_jobinfo()
        jobinfo["nnodes"] = info._nnodes
        jobinfo["result"] = info.result
        jobinfo["returncode"] = info.returncode
        jobinfo["runtime"] = info.runtime
        jobinfo["priority"] = info._priority
        jobinfo["waitstatus"] = info._waitstatus
        jobinfo["nodelist"] = info._nodelist
        jobinfo["nodelist"] = info._nodelist
        jobinfo["exception"] = info._exception.__dict__
        return jobinfo

    # The job does not exist!
    except FileNotFoundError:
        return None
