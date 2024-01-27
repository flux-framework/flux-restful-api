import json
import os
import pwd
import re
import shlex
import subprocess
import time

import flux
import flux.job

from app.core.config import settings

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
submit_script = os.path.join(root, "scripts", "submit-job.py")


class FakeJob:
    def __init__(self, jobid):
        self.jobid = jobid

    def get_id(self):
        return self.jobid


def submit_job(handle, fluxjob, user):
    """
    Submit the job on behalf of user.
    """
    if user and hasattr(user, "user_name"):
        print(f"User submitting job {user.user_name}")
        user = user.user_name
    elif user and isinstance(user, str):
        print(f"User submitting job {user}")

    # If we don't have auth enabled or request is for single-user mode
    if not settings.require_auth or settings.flux_server_mode == "single-user":
        print("Submit in single-user mode.")
        return flux.job.submit_async(handle, fluxjob)

    pw_record = pwd.getpwnam(user)
    user_name = pw_record.pw_name
    # user_uid = pw_record.pw_uid
    # user_gid = pw_record.pw_gid

    # Update the payload for the correct user
    fluxjob.environment["HOME"] = pw_record.pw_dir
    fluxjob.environment["LOGNAME"] = user_name
    fluxjob.environment["USER"] = pw_record.pw_name
    payload = json.dumps(fluxjob.jobspec)

    # We ideally need to pipe the payload into flux python
    try:
        ps = subprocess.Popen(("echo", payload), stdout=subprocess.PIPE)
        output = subprocess.check_output(
            ("sudo", "-E", "-u", user, "flux", "python", submit_script),
            stdin=ps.stdout,
            env=os.environ,
        )
        ps.wait()

    # A flux start without sudo -u flux can cause this
    # This will be caught and returned to the user
    except PermissionError as e:
        raise ValueError(
            f"Permission error: {e}! Are you running the instance as the flux user?"
        )

    jobid = output.decode("utf-8").strip()
    print(f"Submit job {jobid}")
    job = FakeJob(jobid)
    return job


def clean_submit_args(kwargs):
    """
    Clean up submit arguments
    """
    # Clean up Nones
    cleaned = {}
    for k, v in kwargs.items():
        if k == "option_flags" and v is not None:
            option_flags = {}
            flags = v.split(",")
            for flag in flags:
                if "=" not in flag:
                    print('Warning: invalid flag {flag} missing "="')
                    continue
                option, value = flag.split("=", 1)
                option_flags[option] = value
            v = option_flags

        if v is not None:
            cleaned[k] = v
    return cleaned


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
    if num_nodes and int(num_nodes) > settings.flux_nodes:
        errors.append(
            f"The server only has {settings.flux_nodes} nodes, you requested {num_nodes}"
        )

    # Make sure if option_flags defined, we don't have a -o prefix
    option_flags = kwargs.get("option_flags") or {}
    if not isinstance(option_flags, dict):
        errors.append(
            f"Please provide option args as a dictionary, type {type(option_flags)} is invalid."
        )
    else:
        for option, _ in option_flags.items():
            if "-o" in option:
                errors.append(f"Please provide keys without -o, {option} is invalid.")

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


def prepare_job(user, kwargs, runtime=0, workdir=None, envars=None):
    """
    After validation, prepare the job (shared function).
    """
    envars = envars or {}
    option_flags = kwargs.get("option_flags") or {}

    # Generate the flux job
    command = kwargs["command"]
    if isinstance(command, str):
        command = shlex.split(command)

    print(f"⭐️ Command being submit: {command}")

    # Delete command from the kwargs (we added because is required and validated that way)
    # From the command line API client is_launcher won't be here, in the UI it will.
    for key in ["command", "option_flags", "is_launcher"]:
        if key in kwargs:
            del kwargs[key]

    # Assemble the flux job!
    print(f"⭐️ Keyword arguments for flux jobspec: {kwargs}")
    fluxjob = flux.job.JobspecV1.from_command(command, **kwargs)
    for option, value in option_flags.items():
        print(f"⭐️ Setting shell option: {option}={value}")
        fluxjob.setattr_shell_option(option, value)

    # Set an attribute about the owning user
    if user and hasattr(user, "user_name"):
        fluxjob.setattr("user", user.user_name)
        user = user.user_name

    fluxjob.setattr("user", user)

    # Set a provided working directory
    print(f"⭐️ Workdir provided: {workdir}")
    if workdir is not None:
        fluxjob.cwd = workdir

    # A duration of zero (the default) means unlimited
    fluxjob.duration = runtime

    # If we are running as the user, we don't want the current (root) environment
    # However, if we don't provide it, flux stops working.
    # We need to test different ideas for this.
    environment = dict(os.environ)

    # Additional envars in the payload?
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


def cancel_job(jobid, user):
    """
    Request a job to be cancelled by id.

    Returns a message to the user and a return code.
    """
    # TODO need to validate the user owns the job here
    from app.main import app

    try:
        flux.job.cancel(app.handle, jobid)
    # This is usually FileNotFoundError
    except Exception as e:
        return "Job cannot be cancelled: %s." % e, 400
    return "Job is requested to cancel.", 200


def get_job_output(jobid, user=None, delay=None):
    """
    Given a jobid, get the output.

    If there is a delay, we are requesting on demand, so we want to return early.
    """
    # TODO need to validate the user owns the job here
    lines = []
    start = time.time()
    from app.main import app

    jobid = flux.job.JobID(jobid)

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


def list_jobs_detailed(user=None, limit=None, query=None):
    """
    Get a detailed listing of jobs.
    """
    listing = list_jobs(user=user)
    ids = listing.get()["jobs"]
    jobs = {}
    for job in ids:
        # Stop if a limit is defined and we have hit it!
        if limit is not None and len(jobs) >= limit:
            break

        try:
            jobinfo = get_job(job["id"], user=user)

            # Best effort hack to do a query
            if query and not query_job(jobinfo, query):
                continue

            # This will trigger a data table warning
            for needed in ["ranks", "expiration"]:
                if needed not in jobinfo:
                    jobinfo[needed] = ""

            jobs[job["id"]] = jobinfo

        except Exception:
            pass
    return jobs


def list_jobs(user=None):
    """
    Get a simple listing of jobs (just the ids)
    """
    # TODO need to validate the user owns the job here
    from app.main import app

    return flux.job.job_list(app.handle)


def get_simple_job(jobid):
    """
    Not used - an original (simpler) implementation.
    """
    from app.main import app

    info = flux.job.job_list_id(app.handle, jobid, attrs=["all"])
    return json.loads(info.get_str())["job"]


def get_job(jobid, user=None):
    """
    Get details for a job
    """
    # TODO need to validate the user owns the job here
    from app.main import app

    jobid = flux.job.JobID(jobid)

    payload = {"id": jobid, "attrs": ["all"]}
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
