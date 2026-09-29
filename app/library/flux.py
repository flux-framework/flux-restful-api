import json
import os
import pwd
import re
import shlex
import time

import flux
import flux.job
import flux.job.kvslookup

from app.auth.base import is_system_user
from app.core.config import settings
from app.library.env import build_job_environment
from app.library.runas import run_as_user

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
submit_script = os.path.join(root, "scripts", "submit-job.py")


class FakeJob:
    def __init__(self, jobid):
        self.jobid = jobid

    def get_id(self):
        return self.jobid


class JobAccessDenied(Exception):
    """
    The authenticated user does not own the job (and is not a superuser).
    """


def user_name(user):
    """
    The username of a principal (or plain string), or None if anonymous.
    """
    if user is None:
        return None
    if hasattr(user, "user_name"):
        return user.user_name
    return str(user)


def multi_user():
    """
    Multi-user mode: jobs run as the authenticated system user.
    """
    return settings.require_auth and settings.flux_server_mode == "multi-user"


def submit_job(handle, fluxjob, user):
    """
    Submit the job on behalf of user.
    """
    name = user_name(user)

    # Single-user mode (or no auth): submit as the server user
    if not multi_user():
        return flux.job.submit_async(handle, fluxjob)

    # Multi-user: become the user, whose own flux python signs and submits the
    # jobspec. The user's identity variables are set by run_as_user; the job
    # itself gets them from the jobspec environment.
    if not is_system_user(name):
        raise ValueError(f"{name} is not an allowed system account on this server.")
    record = pwd.getpwnam(name)
    fluxjob.environment["HOME"] = record.pw_dir
    fluxjob.environment["LOGNAME"] = record.pw_name
    fluxjob.environment["USER"] = record.pw_name
    payload = json.dumps(fluxjob.jobspec)
    output = run_as_user(["flux", "python", submit_script], name, input=payload)
    # The helper prints the id in F58; return an integer like submit_async does
    return FakeJob(int(flux.job.JobID(output.strip())))


def job_owner(jobid):
    """
    Who owns a job: the (uid, jobspec user attribute) pair, or None if unknown.

    The uid is the system user the job runs as. The user attribute is the API
    user who submitted it, which is what distinguishes users in single-user
    mode where every job runs as the server user.
    """
    from app.main import app

    jobid = flux.job.JobID(jobid)
    try:
        info = flux.job.job_list_id(app.handle, jobid, attrs=["userid"]).get_jobinfo()
    except FileNotFoundError:
        return None
    if multi_user():
        # Only the uid decides ownership; skip the jobspec RPC
        return info.userid, None
    spec = flux.job.kvslookup.job_kvs_lookup(app.handle, jobid, keys=["jobspec"])
    attribute = None
    if spec and spec.get("jobspec"):
        attribute = spec["jobspec"].get("attributes", {}).get("system", {}).get("user")
    return info.userid, attribute


def ensure_job_access(jobid, user):
    """
    Raise JobAccessDenied unless the user may act on the job.

    Anonymous requests (no auth backend) and superusers may act on any job.
    In multi-user mode the job must run as the user's uid; otherwise the job
    must have been submitted by the same API user. Unknown jobs pass, so the
    caller reports them as missing.
    """
    name = user_name(user)
    if name is None or getattr(user, "is_superuser", False):
        return
    owner = job_owner(jobid)
    if owner is None:
        return
    uid, attribute = owner
    if multi_user():
        allowed = uid == pwd.getpwnam(name).pw_uid
    else:
        allowed = attribute == name
    if not allowed:
        raise JobAccessDenied(f"{name} does not own job {jobid}")


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

    # Record the submitting API user; this is how ownership is decided in
    # single-user mode, where every job runs as the server user
    fluxjob.setattr("user", user_name(user))

    # Set a provided working directory
    print(f"⭐️ Workdir provided: {workdir}")
    if workdir is not None:
        fluxjob.cwd = workdir

    # A duration of zero (the default) means unlimited
    fluxjob.duration = runtime

    # Only an allowlist of the server environment, plus the user's envars.
    # The job shell provides FLUX_URI and the FLUX_JOB_* variables itself.
    fluxjob.environment = build_job_environment(envars)
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


def stream_job_output(jobid, user=None):
    """
    Given a jobid, stream the output.

    Callers must check ensure_job_access() before the response starts.
    """
    from app.main import app

    ensure_job_access(jobid, user)
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
    from app.main import app

    ensure_job_access(jobid, user)
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
    lines = []
    start = time.time()
    from app.main import app

    ensure_job_access(jobid, user)
    jobid = flux.job.JobID(jobid)

    # If the submit is too close to the log request, it cannot find the file handle
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
    ids = listing.get_jobs()
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
    Get a simple listing of jobs (just the ids).

    In multi-user mode a non-superuser only sees jobs running as their uid.
    In single-user mode every job runs as the server user, so the listing is
    shared; access to a job's details and output is still per user.
    """
    from app.main import app

    name = user_name(user)
    if multi_user() and name and not getattr(user, "is_superuser", False):
        return flux.job.job_list(app.handle, userid=pwd.getpwnam(name).pw_uid)
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
    from app.main import app

    ensure_job_access(jobid, user)
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
