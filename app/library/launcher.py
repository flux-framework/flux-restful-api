import os
import shlex
import subprocess

from app.core.config import settings


def launch(kwargs, workdir=None, envars=None):
    """
    Launch a job with a known launcher
    """
    envars = envars or {}

    # Generate the flux job
    command = kwargs["command"]
    if isinstance(command, str):
        command = shlex.split(command)
    print(f"⭐️ Command being submit: {command}")

    # We don't allow commands willy nilly
    if command[0] not in settings.known_launchers:
        return f"{command[0]} is not a known launcher. "

    # Delete command from the kwargs (we added because is required and validated that way)
    del kwargs["command"]

    # Additional envars in the payload?
    environment = dict(os.environ)
    environment.update(envars)

    print(f"⭐️ Workdir provided: {workdir}")
    print(f"⭐️ Command being submit: {command}")

    # TODO need to install conda stuffs
    # Submit using subprocess (we can see output in terminal)
    try:
        subprocess.Popen(
            command, cwd=workdir, env=environment, stdout=None, stderr=None, stdin=None
        )
    except Exception as e:
        return str(e)
    return "Job submit, see jobs table for spawned jobs."
