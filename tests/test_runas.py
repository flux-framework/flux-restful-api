"""
Unit tests for running helpers as a user (no Flux needed).

Switching to the current uid is skipped, so these run without root. The
real uid switch is covered by test_run_as_other_user_as_root, which runs
in CI's root pass.
"""

import os
import pwd
import subprocess

import pytest

from app.core.config import settings
from app.library import runas

ME = pwd.getpwuid(os.getuid())


@pytest.fixture
def allow_me(monkeypatch):
    """
    CI runs as root, which FLUX_MIN_UID refuses (that has its own test);
    let the account running the tests be used as the target.
    """
    monkeypatch.setattr(settings, "min_uid", min(settings.min_uid, os.getuid()))


def other_unprivileged_user():
    """
    Some unprivileged system account that is not the one running the tests.
    """
    for record in pwd.getpwall():
        if 1000 <= record.pw_uid < 65000 and record.pw_uid != os.getuid():
            return record.pw_name
    return None


def test_no_switch_for_current_uid():
    assert runas.switch_user_kwargs(ME) == {}


def test_switch_sets_uid_gid_and_groups():
    record = pwd.struct_passwd(
        ("someone", "x", 4242, 4343, "", "/home/someone", "/bin/sh")
    )
    kwargs = runas.switch_user_kwargs(record)
    assert kwargs["user"] == 4242
    assert kwargs["group"] == 4343
    # Supplementary groups come from the group database; the primary gid is
    # always included
    assert 4343 in kwargs["extra_groups"]


def test_run_passes_switch_to_subprocess(monkeypatch):
    """
    The switch is handed to subprocess (which does it in the child after
    fork) rather than done in preexec_fn, which is unsafe with threads.
    """
    other = other_unprivileged_user()
    if other is None:
        pytest.skip("needs another unprivileged account")
    record = pwd.getpwnam(other)
    monkeypatch.setattr(os, "getuid", lambda: 0)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout=b"ok\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert runas.run_as_user(["id"], other) == "ok\n"
    (kwargs,) = calls
    assert kwargs["user"] == record.pw_uid
    assert kwargs["group"] == record.pw_gid
    assert record.pw_gid in kwargs["extra_groups"]
    assert "preexec_fn" not in kwargs
    assert kwargs["env"]["USER"] == other


def test_user_environment_has_identity_and_no_secrets(monkeypatch):
    monkeypatch.setenv("FLUX_TOKEN", "server-secret")
    monkeypatch.setenv("FLUX_URI", "local:///tmp/flux/local-0")
    env = runas.user_environment(ME, {"PANCAKES": "yes"})
    assert env["HOME"] == ME.pw_dir
    assert env["USER"] == ME.pw_name
    assert env["LOGNAME"] == ME.pw_name
    assert env["FLUX_URI"] == "local:///tmp/flux/local-0"
    assert env["PANCAKES"] == "yes"
    assert "FLUX_TOKEN" not in env


def test_run_as_self(allow_me):
    assert runas.run_as_user(["id", "-u"], ME.pw_name).strip() == str(os.getuid())
    assert runas.run_as_user(["cat"], ME.pw_name, input="hello").strip() == "hello"


def test_run_as_other_user_as_root():
    """
    A real uid switch, which only root can do (CI's first pass).
    """
    other = other_unprivileged_user()
    if os.getuid() != 0 or other is None:
        pytest.skip("needs root and another unprivileged account")
    record = pwd.getpwnam(other)
    assert runas.run_as_user(["id", "-u"], other).strip() == str(record.pw_uid)
    assert runas.run_as_user(["id", "-g"], other).strip() == str(record.pw_gid)
    assert runas.run_as_user(["sh", "-c", "echo $HOME"], other).strip() == record.pw_dir


def test_run_as_unknown_or_privileged_user_fails():
    with pytest.raises(runas.RunAsError, match="not an allowed system account"):
        runas.run_as_user(["id"], "no-such-user-xyz")
    # root is always refused, even when we are root (FLUX_MIN_UID)
    with pytest.raises(runas.RunAsError, match="not an allowed system account"):
        runas.run_as_user(["id"], "root")


def test_run_as_other_user_requires_root():
    other = other_unprivileged_user()
    if os.getuid() == 0 or other is None:
        pytest.skip("needs to run unprivileged with another unprivileged account")
    with pytest.raises(runas.RunAsError, match="requires the server to run as root"):
        runas.run_as_user(["id"], other)


def test_run_as_reports_failures(allow_me):
    with pytest.raises(runas.RunAsError, match="exited with code 3"):
        runas.run_as_user(["sh", "-c", "echo boom >&2; exit 3"], ME.pw_name)
    with pytest.raises(runas.RunAsError, match="boom"):
        runas.run_as_user(["sh", "-c", "echo boom >&2; exit 3"], ME.pw_name)
    with pytest.raises(runas.RunAsError, match="Could not run"):
        runas.run_as_user(["/no/such/binary"], ME.pw_name)
