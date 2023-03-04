import json
import os
import pwd
import shlex
import subprocess

import app.library.env as env
from app.core.config import settings

# Terminal functions to handle submitting on behalf of a user

job_format = "{id.f58:>12} {username:<8.8} {name:<10.10+} {status:>9.9} {ntasks:>6} {nnodes:>6h} {t_submit!d:%b%d %R::>12} {t_remaining!F:>12h} {contextual_time!F:>8h}"
fields = [
    "id",
    "user",
    "name",
    "status",
    "ntasks",
    "nnodes",
    "time_submit",
    "time_remaining",
    "time_contextual",
]


class JobId:
    """
    A fake Flux Future that can return a job_id
    """

    def __init__(self, jobid):
        self.job_id = jobid

    def get_id(self):
        return self.job_id


def run_as_user(command, user, cwd=None, request_env=None):
    """
    Run a command as a user
    """
    pw_record = pwd.getpwnam(user)
    user_name = pw_record.pw_name
    user_uid = pw_record.pw_uid
    user_gid = pw_record.pw_gid

    # Even for a user this should be populated with dummy paths, etc.
    env = {}

    # cwd will bork on an empty string
    cwd = cwd or None

    print(f"🧾️ Running command as {user_name}")
    env["HOME"] = pw_record.pw_dir
    env["LOGNAME"] = user_name
    env["USER"] = pw_record.pw_name

    # Ensure we pass forward the flux uri
    flux_uri = os.environ.get("FLUX_URI")
    if flux_uri:
        env["FLUX_URI"] = flux_uri

    # Update the environment, if provided
    if request_env is not None:
        env.update(request_env)

    # Run command as the user
    print("⭐️ " + " ".join(command))
    print(cwd)
    print(env)
    process = subprocess.Popen(
        command,
        preexec_fn=demote(user_uid, user_gid),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
    )

    # Let the calling function handle the return value parsing
    return process.communicate()


def prepare_job(kwargs, runtime, workdir, envars):
    """
    Prepare a job to submit on the command line.
    """
    envars = envars or {}
    option_flags = kwargs.get("option_flags") or {}

    # Generate the flux job
    command = kwargs["command"]
    if isinstance(command, str):
        command = shlex.split(command)

    print(f"⭐️ Command being submit: {command}")

    # Mapping of keys to command
    submit = ["flux", "submit"]

    for option, value in option_flags.items():
        print(f"⭐️ Setting shell option: {option}={value}")
        submit += ["-o", f"{option}={value}"]

    if workdir is not None:
        submit.append(f"--cwd={workdir}")

    # TODO add
    # -c, --cores-per-task=N     Number of cores to allocate per task
    # -g, --gpus-per-task=N      Number of GPUs to allocate per task
    if "num_nodes" in kwargs:
        submit.append(f"--nodes={kwargs['num_nodes']}")

    if "num_tasks" in kwargs:
        submit.append(f"--ntasks={kwargs['num_tasks']}")

    # It says cores should not be used with ntasks
    elif "cores" in kwargs:
        submit.append(f"--cores={kwargs['cores']}")

    # A duration of zero (the default) means unlimited
    submit.append("--time-limit={runtime}")

    # Assemble the flux job!
    print(f"⭐️ Flux submit {' '.join(submit)}")

    # If we are running as the user, we don't want the current (root) environment
    # This isn't perfect because it's artifically created, but it ensures we have paths
    if settings.enable_pam:
        environment = env.user_env
    else:
        environment = dict(os.environ)

    # Additional envars in the payload - add to the front
    environment.update(envars)

    # Assemble the flux job!
    return {"command": submit, "env": environment, "cwd": workdir}


def submit_job(fluxjob, user):
    """
    Submit a job on behalf of a user.
    """
    # Convert jobspec into job
    # Flux submit as the user
    result = run_as_user(
        fluxjob["command"], request_env=fluxjob["env"], user=user, cwd=fluxjob["cwd"]
    )
    jobid = (result[0].decode("utf-8")).strip()
    return JobId(jobid)


def cancel_job(jobid, user):
    """
    Cancel a job for a user
    """
    command = ["flux", "job", "cancel", jobid]
    result = run_as_user(command, user=user)
    jobid = (result[0].decode("utf-8")).strip()
    if "inactive" in jobid:
        return "Job cannot be cancelled: %s." % jobid, 400
    return "Job is requested to cancel.", 200


def get_job_output(jobid, user, delay=None):
    """
    Given a jobid, get the output.

    If there is a delay, we are requesting on demand, so we want to return early.
    """
    lines = []
    command = ["flux", "job", "info", jobid, "guest.output"]
    result = run_as_user(command, user=user)
    lines = (result[0].decode("utf-8")).strip()

    output = ""
    for line in lines.split("\n"):
        try:
            content = json.loads(line)
            if "context" in content and "data" in content["context"]:
                output += content["context"]["data"]
        except Exception:
            print(line)
            pass
    return output


def demote(user_uid, user_gid):
    """
    Demote the user to a specific gid/gid
    """

    def result():
        os.setgid(user_gid)
        os.setuid(user_uid)

    return result


def get_job(jobid, user):
    """
    Get details for a job

    This is not currently used, instead we pass a user to job list.
    """
    command = ["flux", "jobs", jobid, "-o", job_format, "--suppress-header"]
    result = run_as_user(command, user=user)
    jobid = (result[0].decode("utf-8")).strip()
    jobid = [x for x in jobid.split(" ") if x]
    jobinfo = {}
    for field in fields:
        jobinfo[field] = jobid.pop(0)
    return jobinfo
