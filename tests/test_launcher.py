"""
Unit tests for launching workflow tools (no Flux needed).
"""

import subprocess

from app.library import launcher


def test_unknown_launcher_is_refused(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append(k))
    message = launcher.launch({"command": "rm -rf /"})
    assert "not a known launcher" in message
    assert calls == []


def test_launcher_gets_flux_uri_but_no_secrets(monkeypatch):
    """
    Launchers run on the server, outside a job shell, and submit jobs to
    this instance themselves, so they need FLUX_URI (which a job shell would
    otherwise provide) but must not see server secrets.
    """
    monkeypatch.setenv("FLUX_URI", "local:///tmp/flux/local-0")
    monkeypatch.setenv("FLUX_TOKEN", "server-secret")
    monkeypatch.setenv("FLUX_SECRET_KEY", "shared-secret")
    monkeypatch.delenv("FLUX_JOB_ENV_PASSTHROUGH", raising=False)
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    message = launcher.launch(
        {"command": "nextflow run main.nf"},
        workdir="/tmp",
        envars={"NXF_ANSI_LOG": "false"},
    )
    assert "Job submit" in message
    ((command, kwargs),) = calls
    assert command == ["nextflow", "run", "main.nf"]
    assert kwargs["cwd"] == "/tmp"
    env = kwargs["env"]
    assert env["FLUX_URI"] == "local:///tmp/flux/local-0"
    assert env["NXF_ANSI_LOG"] == "false"
    assert "PATH" in env
    assert "FLUX_TOKEN" not in env
    assert "FLUX_SECRET_KEY" not in env
