"""
Run a command as another system user (multi-user mode).

Flux jobs must be signed by the user they run as: munge stamps a credential
with the real uid of the calling process, so the server cannot sign on a
user's behalf. Instead, the server (running as root) becomes the user for
the duration of a helper process, whose own `flux python` signs and submits
the jobspec. The Flux instance then accepts it as a guest job and flux-imp
launches it as that user.

subprocess switches the child to the user's uid, gid and groups after
fork, so no sudoers configuration is needed. Only root can switch to another
user; a switch to the current uid is skipped, which is what happens in tests.
"""

import os
import pwd
import subprocess
from typing import Dict, Optional, Sequence

from app.auth.base import is_system_user
from app.library.env import build_helper_environment


class RunAsError(RuntimeError):
    """The command could not be run as the user, or exited non-zero."""


def switch_user_kwargs(record: pwd.struct_passwd) -> Dict:
    """
    Keyword arguments for subprocess.run that make the child run as the user.

    subprocess does the switch itself in the child after fork (setgroups,
    setgid, setuid, in that order), which is safe in a threaded server where
    preexec_fn is not. No switch is needed when we already are the user.
    """
    if os.getuid() == record.pw_uid:
        return {}
    return {
        "user": record.pw_uid,
        "group": record.pw_gid,
        "extra_groups": os.getgrouplist(record.pw_name, record.pw_gid),
    }


def user_environment(record: pwd.struct_passwd, extra: Optional[Dict] = None) -> Dict:
    """
    The environment for a helper process run as the user: the allowlisted
    server environment plus FLUX_URI, with the user's own identity variables.
    """
    environment = build_helper_environment()
    environment.update(
        {"HOME": record.pw_dir, "USER": record.pw_name, "LOGNAME": record.pw_name}
    )
    environment.update(extra or {})
    return environment


def run_as_user(
    command: Sequence[str],
    username: str,
    input: Optional[str] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict] = None,
) -> str:
    """
    Run a command as the user and return its stdout. Raises RunAsError.
    """
    # Never become a privileged or unknown account, whatever produced the
    # name (see FLUX_MIN_UID). The request dependencies check this too; this
    # is the authoritative check at the point the privilege is used.
    if not is_system_user(username):
        raise RunAsError(
            f"{username} is not an allowed system account on this host "
            "(unknown, or below FLUX_MIN_UID)."
        )
    record = pwd.getpwnam(username)

    if os.getuid() not in (0, record.pw_uid):
        raise RunAsError(
            f"Running as {username} requires the server to run as root "
            f"(it is uid {os.getuid()})."
        )

    try:
        result = subprocess.run(
            list(command),
            input=input.encode("utf-8") if input is not None else None,
            capture_output=True,
            cwd=cwd or None,
            env=user_environment(record, env),
            check=False,
            **switch_user_kwargs(record),
        )
    except OSError as e:
        raise RunAsError(f"Could not run {command[0]} as {username}: {e}")

    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RunAsError(
            f"{command[0]} exited with code {result.returncode} as {username}: {error}"
        )
    return result.stdout.decode("utf-8", errors="replace")
