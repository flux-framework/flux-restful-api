import os
import pwd
import subprocess
import time

# Terminal functions to handle submitting on behalf of a user


class JobId:
    """
    A fake Flux Future that can return a job_id
    """

    def __init__(self, jobid):
        self.job_id = jobid

    def get_id(self):
        return self.job_id


def run_as_user(command, request_env, user, cwd):
    """
    Run a command as a user
    """
    pw_record = pwd.getpwnam(user)
    user_name = pw_record.pw_name
    user_uid = pw_record.pw_uid
    user_gid = pw_record.pw_gid
    env = os.environ.copy()

    env["HOME"] = pw_record.pw_dir
    env["LOGNAME"] = user_name
    env["USER"] = pw_record.pw_name
    env.update(request_env)

    # Run command as the user
    print("⭐️ " + " ".join(command))
    process = subprocess.Popen(
        command,
        preexec_fn=demote(user_uid, user_gid),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
    )

    # Let the calling function handle the return value parsing
    return process.communicate()


def submit_job(jobspec, user):
    """
    Submit a job on behalf of a user.
    """
    # Prepare the command
    command = ["flux", "mini", "submit"]
    for resource in jobspec.resources:
        if resource["with"][0]["type"] == "core":
            command += ["--cores", str(resource["count"])]

    for cmd in jobspec.tasks:
        if "command" in cmd:
            command += cmd["command"]
            break

    # Flux submit as the user
    result = run_as_user(command, jobspec.environment, user, jobspec.cwd)
    jobid = (result[0].decode("utf-8")).strip()
    return JobId(jobid)


def get_job_output(jobid, user, delay=None):
    """
    Given a jobid, get the output.

    If there is a delay, we are requesting on demand, so we want to return early.
    """
    lines = []
    start = time.time()

    command = ["flux", "job", "info", jobid, "guest.output"]
    import code

    code.interact(local=locals())

    # TODO work on this tomorrow
    # If the submit is too close to the log reqest, it cannot find the file handle
    # It could be also the jobid cannot be found.
    # what is equivalent on command line for:
    #    for line in flux.job.event_watch(app.handle, jobid, "guest.output"):


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
    """
    command = ["flux", "job", "info", jobid, "guest.output"]
    import code

    code.interact(local=locals())

    # TODO How to reproduce this?
    # payload = {"id": int(jobid), "attrs": ["all"]}
    # rpc = flux.job.list.JobListIdRPC(app.handle, "job-list.list-id", payload)
    # try:
    #    jobinfo = rpc.get()
    # return jobinfo
