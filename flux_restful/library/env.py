"""
The environment given to jobs and launchers.

The server's own environment must not be copied into jobs: it holds the
server's configuration and secrets (FLUX_TOKEN, FLUX_SECRET_KEY,
FLUX_TOKEN_SIGNING_KEY, ...) and in multi-user mode the job runs as someone
else. A job only needs a small set of variables to run and to talk to Flux;
the job shell provides FLUX_URI and the FLUX_JOB_* variables itself.
Operators can pass more with FLUX_JOB_ENV_PASSTHROUGH (comma separated
names or fnmatch patterns).
"""

import fnmatch
import os
from typing import Dict, Iterable, Optional

# Always passed through from the server environment, when set.
JOB_ENV_ALLOWLIST = [
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "LANG",
    "LANGUAGE",
    "LC_*",
    "TERM",
    "TZ",
    "TMPDIR",
    # Needed for flux python / modules when Flux is not on the default paths
    "PYTHONPATH",
    "LD_LIBRARY_PATH",
    "MANPATH",
    "LUA_PATH",
    "LUA_CPATH",
    # Flux runtime paths exported by flux start (never FLUX_URI: the job
    # shell sets that, and never the server's FLUX_* configuration)
    "FLUX_EXEC_PATH",
    "FLUX_MODULE_PATH",
    "FLUX_CONNECTOR_PATH",
    "FLUX_PMI_LIBRARY_PATH",
]


def passthrough_patterns() -> list:
    """
    Extra names or patterns from FLUX_JOB_ENV_PASSTHROUGH.
    """
    value = os.environ.get("FLUX_JOB_ENV_PASSTHROUGH") or ""
    return [item.strip() for item in value.split(",") if item.strip()]


def is_allowed(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def build_job_environment(
    extra: Optional[Dict[str, str]] = None, source: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    The environment for a job: allowlisted server variables plus user extras.

    User provided variables (from the submit request) take precedence.
    """
    source = os.environ if source is None else source
    patterns = JOB_ENV_ALLOWLIST + passthrough_patterns()
    environment = {
        name: value for name, value in source.items() if is_allowed(name, patterns)
    }
    for name, value in (extra or {}).items():
        environment[str(name)] = str(value)
    return environment


def build_helper_environment(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    The environment for processes that run on the server (not inside a job)
    and must reach this Flux instance: the multi-user submit script, and
    launchers such as nextflow or snakemake that submit their own jobs.
    The job environment plus FLUX_URI, which the job shell would otherwise
    provide.
    """
    environment = build_job_environment(extra)
    if "FLUX_URI" in os.environ:
        environment["FLUX_URI"] = os.environ["FLUX_URI"]
    return environment
