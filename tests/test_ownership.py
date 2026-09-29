"""
Integration tests for job ownership (need a running Flux instance).
"""

import os
import pwd
import time

import pytest

import app.auth as auth
import app.library.flux as flux_cli
from app.core.config import settings

ME = pwd.getpwuid(os.getuid()).pw_name


def token_for(db, username, password):
    backend = auth.get_backend()
    principal = backend.authenticate(db, username, password)
    return {"Authorization": "Bearer " + backend.issue_token(principal)}


def submit(client, headers, command="sleep 60"):
    response = client.post(
        "/v1/jobs/submit", params={"command": command}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def wait_inactive(client, headers, jobid, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/v1/jobs/{jobid}", headers=headers).json()
        if job["state"] == "INACTIVE":
            return
        time.sleep(0.5)
    raise AssertionError(f"job {jobid} did not finish")


def listed_ids(client, headers):
    return [job["id"] for job in client.get("/v1/jobs", headers=headers).json()["jobs"]]


def test_single_user_mode_jobs_are_owned_by_the_api_user(
    client, db, use_backend, make_user
):
    use_backend("database", flux_server_mode="single-user")
    make_user("alice", "wonderland")
    make_user("bob", "builder")
    make_user("root-user", "toor", superuser=True)
    alice = token_for(db, "alice", "wonderland")
    bob = token_for(db, "bob", "builder")
    admin = token_for(db, "root-user", "toor")

    jobid = submit(client, alice)

    # Reading output of a running job blocks until it ends, so use a finished
    # job for the output checks
    done = submit(client, alice, command="echo pancakes")
    wait_inactive(client, alice, done)

    # The owner and a superuser may see, read, and cancel it
    assert client.get(f"/v1/jobs/{jobid}", headers=alice).status_code == 200
    assert client.get(f"/v1/jobs/{done}/output", headers=alice).status_code == 200
    assert client.get(f"/v1/jobs/{jobid}", headers=admin).status_code == 200

    # Another user may not, including the output stream, which is checked
    # before the response starts
    for path in [f"/v1/jobs/{jobid}", f"/v1/jobs/{done}/output"]:
        response = client.get(path, headers=bob)
        assert response.status_code == 403, path
        assert "does not own" in response.json()["detail"]
    with client.stream(
        "GET", f"/v1/jobs/{done}/output/stream", headers=bob
    ) as response:
        assert response.status_code == 403
    with client.stream(
        "GET", f"/v1/jobs/{done}/output/stream", headers=alice
    ) as response:
        assert response.status_code == 200
        assert "pancakes" in response.read().decode()
    assert client.post(f"/v1/jobs/{jobid}/cancel", headers=bob).status_code == 403
    assert client.get(f"/job/{done}", auth=("bob", "builder")).status_code == 403
    assert client.get(f"/job/{done}", auth=("alice", "wonderland")).status_code == 200

    # The listing is shared in single-user mode (every job runs as the server user)
    assert jobid in listed_ids(client, bob)

    response = client.post(f"/v1/jobs/{jobid}/cancel", headers=alice)
    assert response.status_code == 200, response.text


def test_anonymous_and_unknown_jobs(client, use_backend):
    use_backend("none")
    jobid = submit(client, {})
    # No auth backend: nobody is denied
    flux_cli.ensure_job_access(jobid, None)
    # Unknown jobs are not an access error (the caller reports them missing)
    flux_cli.ensure_job_access(999999999999, None)


def other_unprivileged_user():
    """
    Some unprivileged system account that is not the one running the tests.
    """
    for record in pwd.getpwall():
        if 1000 <= record.pw_uid < 65000 and record.pw_uid != os.getuid():
            return record.pw_name
    return None


def test_multi_user_mode_submits_as_the_user(
    client, db, use_backend, make_user, monkeypatch
):
    """
    Demoting to the current uid is a no-op, so the multi-user submit path
    (become the user, whose own flux python signs and submits) runs here
    without root, as long as the API user is the unix user running the tests.
    """
    other_name = other_unprivileged_user()
    if other_name is None:
        pytest.skip("needs another unprivileged system account")
    use_backend("database", flux_server_mode="multi-user")
    # CI runs this as root, which FLUX_MIN_UID would refuse; allow ourselves
    monkeypatch.setattr(settings, "min_uid", min(settings.min_uid, os.getuid()))
    make_user(ME, "mypassword")
    make_user(other_name, "otherpass")  # a real system account that is not us
    me = token_for(db, ME, "mypassword")
    other = token_for(db, other_name, "otherpass")

    jobid = submit(client, me, command="sleep 30")
    assert isinstance(jobid, int)
    assert flux_cli.job_owner(jobid)[0] == os.getuid()

    # Listing and access are by uid
    assert jobid in listed_ids(client, me)
    assert jobid not in listed_ids(client, other)
    assert client.get(f"/v1/jobs/{jobid}", headers=other).status_code == 403
    assert client.post(f"/v1/jobs/{jobid}/cancel", headers=other).status_code == 403
    response = client.post(f"/v1/jobs/{jobid}/cancel", headers=me)
    assert response.status_code == 200, response.text

    # Submitting as a user we cannot become (unprivileged server), or who
    # cannot reach our Flux instance (root server), is a clean 400, not a crash
    response = client.post("/v1/jobs/submit", params={"command": "true"}, headers=other)
    assert response.status_code == 400, response.text
    assert "Error" in response.json()
