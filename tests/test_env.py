"""
Unit tests for the job environment allowlist (no Flux needed).
"""

import re

from app.library import env

SERVER_ENV = {
    "PATH": "/usr/bin",
    "HOME": "/home/flux",
    "USER": "flux",
    "LC_ALL": "C.UTF-8",
    "PYTHONPATH": "/usr/lib/flux/python3.11",
    "FLUX_EXEC_PATH": "/usr/libexec/flux/cmd",
    "FLUX_URI": "local:///tmp/flux/local-0",
    "FLUX_TOKEN": "server-password",
    "FLUX_SECRET_KEY": "shared-secret",
    "FLUX_TOKEN_SIGNING_KEY": "signing-key",
    "FLUX_USER": "fluxuser",
    "AWS_SECRET_ACCESS_KEY": "aws",
    "MY_APP_SETTING": "yes",
}


def test_allowlist_drops_secrets_and_server_config(monkeypatch):
    monkeypatch.delenv("FLUX_JOB_ENV_PASSTHROUGH", raising=False)
    result = env.build_job_environment(source=SERVER_ENV)
    assert result == {
        "PATH": "/usr/bin",
        "HOME": "/home/flux",
        "USER": "flux",
        "LC_ALL": "C.UTF-8",
        "PYTHONPATH": "/usr/lib/flux/python3.11",
        "FLUX_EXEC_PATH": "/usr/libexec/flux/cmd",
    }


def test_user_envars_are_added_and_win(monkeypatch):
    monkeypatch.delenv("FLUX_JOB_ENV_PASSTHROUGH", raising=False)
    result = env.build_job_environment(
        {"PANCAKES": "yes", "PATH": "/opt/bin"}, SERVER_ENV
    )
    assert result["PANCAKES"] == "yes"
    assert result["PATH"] == "/opt/bin"
    assert "FLUX_TOKEN" not in result


def test_passthrough_patterns(monkeypatch):
    monkeypatch.setenv("FLUX_JOB_ENV_PASSTHROUGH", "MY_APP_*, AWS_SECRET_ACCESS_KEY")
    result = env.build_job_environment(source=SERVER_ENV)
    assert result["MY_APP_SETTING"] == "yes"
    assert result["AWS_SECRET_ACCESS_KEY"] == "aws"
    assert "FLUX_TOKEN" not in result


def test_helper_environment_adds_flux_uri(monkeypatch):
    monkeypatch.delenv("FLUX_JOB_ENV_PASSTHROUGH", raising=False)
    for key, value in SERVER_ENV.items():
        monkeypatch.setenv(key, value)
    result = env.build_helper_environment({"PANCAKES": "yes"})
    assert result["FLUX_URI"] == SERVER_ENV["FLUX_URI"]
    assert result["PANCAKES"] == "yes"
    assert "FLUX_SECRET_KEY" not in result
    assert "FLUX_TOKEN_SIGNING_KEY" not in result


def test_no_server_setting_is_allowlisted():
    """
    Every FLUX_* variable read by app/core/config.py is server configuration
    and must never reach a job by default.
    """
    from app.core import config

    with open(config.__file__) as fd:
        names = set(re.findall(r'"(FLUX_[A-Z_]+)"', fd.read()))
    assert names, "expected to find FLUX_* settings in config.py"
    for name in names:
        assert not env.is_allowed(name, env.JOB_ENV_ALLOWLIST), name
