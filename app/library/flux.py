import json
import os
import re
import shlex
import time

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
    print(f"⭐️ Command being submit: {command}")

    # Delete command from the kwargs (we added because is required and validated that way)
    del kwargs["command"]
    fluxjob = flux.job.JobspecV1.from_command(command, **kwargs)

    print(f"⭐️ Workdir provided: {workdir}")
    if workdir is not None:
        fluxjob.cwd = workdir

    # A duration of zero (the default) means unlimited
    fluxjob.duration = runtime

    # Additional envars in the payload?
    environment = dict(os.environ)
    environment.update(envars)
    fluxjob.environment = environment
    return fluxjob


def query_job(jobinfo, query):
    """
    This would be better suited for a database, but should work for small numbers.
    """
    searchstr = "".join([str(x) for x in list(jobinfo.values())])
    return re.search(query, searchstr)


def query_jobs(contenders, query):
    """
    Wrapper to query more than one job.
    """
    jobs = []
    for contender in contenders:
        if not query_job(contender, query):
            continue
        jobs.append(contender)
    return jobs


def stream_job_output(jobid):
    """
    Given a jobid, stream the output
    """
    from app.main import app

    try:
        for line in flux.job.event_watch(app.handle, jobid, "guest.output"):
            if "data" in line.context:
                yield line.context["data"]
    except Exception:
        pass


def get_job_output(jobid, delay=None):
    """
    Given a jobid, get the output.

    If there is a delay, we are requesting on demand, so we want to return early.
    """
    lines = []
    start = time.time()
    from app.main import app

    # If the submit is too close to the log reqest, it cannot find the file handle
    # It could be also the jobid cannot be found.
    try:
        for line in flux.job.event_watch(app.handle, jobid, "guest.output"):
            if "data" in line.context:
                lines.append(line.context["data"])
            now = time.time()
            if delay is not None and (now - start) > delay:
                return lines
    except Exception:
        pass
    return lines


def list_jobs_detailed(limit=None, query=None):
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
            jobinfo = get_job(job["id"])

            # Best effort hack to do a query
            if query and not query_job(jobinfo, query):
                continue
            jobs[job["id"]] = jobinfo
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
        jobinfo = rpc.get()

    # The job does not exist!
    except FileNotFoundError:
        return None

    jobinfo = jobinfo["job"]

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

    # Only appears after finished?
    if "duration" not in jobinfo:
        jobinfo["duration"] = ""
    return jobinfo
