import base64
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)

sys.path.insert(0, root)

from app.main import app  # noqa

client = TestClient(app)

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)

sys.path.insert(0, root)


def get_basic_auth(username, password):
    auth_str = "%s:%s" % (username, password)
    return base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")


def get_headers():
    auth_header = get_basic_auth(flux_user, flux_token)
    if isinstance(auth_header, bytes):
        auth_header = auth_header.decode("utf-8")
    return {"Authorization": "Basic %s" % auth_header}


# Do we want auth?
test_auth = False
test_pam_auth = False
test_pam_auth_fail = False
headers = {}

if os.environ.get("TEST_AUTH"):
    # Define authentication in environment for server
    flux_user = "fluxuser"
    flux_token = "12345"
    os.environ["FLUX_USER"] = flux_user
    os.environ["FLUX_TOKEN"] = flux_token
    os.environ["FLUX_REQUIRE_AUTH"] = "true"
    test_auth = True
    headers = get_headers()

elif os.environ.get("TEST_PAM_AUTH"):
    # Define authentication in environment for server
    flux_user = "fluxuser"
    flux_token = "12345"
    os.environ["FLUX_REQUIRE_AUTH"] = "true"
    os.environ["FLUX_ENABLE_PAM"] = "true"
    test_pam_auth = True
    test_pam_auth_fail = os.environ["TEST_PAM_AUTH_FAIL"] == "true"
    print(test_pam_auth_fail)
    headers = get_headers()

skip_if_expected_fail = pytest.mark.skipif(test_pam_auth_fail, reason="Unix stuff")


def test_failure():
    """
    Test failing auth
    """
    response = client.get("/v1/jobs", headers=headers)
    if test_pam_auth_fail is True:
        assert response.status_code != 200
    else:
        assert response.status_code == 200


@skip_if_expected_fail
def test_submit_list_job():
    """
    Test a manual submission
    """
    # No jobs are submit!
    response = client.get("/v1/jobs", headers=headers)
    assert response.status_code == 200
    assert not response.json()["jobs"]

    # Now submit a job, ensure we get one job back
    response = client.post(
        "/v1/jobs/submit", json={"command": "sleep 5"}, headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    assert "id" in result
    jobid = result["id"]

    # List jobs with and without details
    response = client.get("/v1/jobs", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert "jobs" in result
    result = result["jobs"]
    assert len(result) == 1
    assert result[0]["id"] == jobid

    response = client.get("/v1/jobs", headers=headers, json={"details": True})
    assert response.status_code == 200
    result = response.json()
    assert str(jobid) in result
    result = result[str(jobid)]

    # There are 25 total
    assert len(result) > 20
    assert result["id"] == jobid

    # Testing asking for a listing
    response = client.get(
        "/v1/jobs", headers=headers, json={"details": True, "listing": True}
    )
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert result[0]["id"] == jobid

    # And setting an integer limit (only relevant for details)
    response = client.get(
        "/v1/jobs", headers=headers, json={"limit": 0, "details": True}
    )
    assert response.status_code == 200
    result = response.json()
    assert not result


@skip_if_expected_fail
def test_cancel_job():
    # Now submit a job, ensure we get one job back
    response = client.post(
        "/v1/jobs/submit", json={"command": "sleep 10"}, headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    jobid = result["id"]
    response = client.post(f"/v1/jobs/{jobid}/cancel", headers=headers)
    assert response.status_code == 200
    # TODO we don't have way to actually verify that cancel happened


@skip_if_expected_fail
def test_submit_option_flags():
    """
    Test that option flags are parsed.
    """
    # Submit a job with invalid flags
    response = client.post(
        "/v1/jobs/submit",
        json={"command": "sleep 1", "option_flags": "invalid"},
        headers=headers,
    )
    assert response.status_code == 400
    result = response.json()
    errors = result.get("Errors")
    assert errors
    assert "is invalid" in errors[0]

    # Another invalid pattern
    response = client.post(
        "/v1/jobs/submit",
        json={"command": "sleep 1", "option_flags": {"-ompi": "nope"}},
        headers=headers,
    )
    assert response.status_code == 400
    result = response.json()
    errors = result.get("Errors")
    assert errors
    assert "keys without -o" in errors[0]

    # Valid
    response = client.post(
        "/v1/jobs/submit",
        json={"command": "sleep 1", "option_flags": {"ompi": "openmpi@5"}},
        headers=headers,
    )
    assert response.status_code == 200
    result = response.json()
    assert "id" in result


@skip_if_expected_fail
def test_job_output():
    """
    Test endpoint to retrieve list of job output
    """

    # Now submit a job, ensure we get one job back
    response = client.post(
        "/v1/jobs/submit", json={"command": "echo pancakes 🥞️🥞️🥞️"}, headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    jobid = result["id"]
    res = client.get(f"/v1/jobs/{jobid}/output", headers=headers)
    assert response.status_code == 200
    lines = res.json()

    # First try, often we won't have output yet
    if "Message" in lines:
        assert "not exist yet" in lines["Message"]
    time.sleep(3)

    # Try again - we should have it after a sleep
    res = client.get(f"/v1/jobs/{jobid}/output", headers=headers)
    assert response.status_code == 200
    lines = res.json()
    assert "Output" in lines
    assert "pancakes 🥞️🥞️🥞️\n" in lines["Output"]


@skip_if_expected_fail
def test_job_query():
    """
    Test endpoint to query jobs
    """
    # Submit 5 jobs
    for _ in range(5):
        client.post("/v1/jobs/submit", json={"command": "sleep 1"}, headers=headers)

    response = client.get("/v1/jobs/search", headers=headers)
    assert response.status_code == 200
    result = response.json()

    for key in ["recordsTotal", "recordsFiltered", "draw", "data"]:
        assert key in result
    total = result["recordsTotal"]
    assert len(result["data"]) == total

    # Ask to start at 2 (should be one less record)
    response = client.get("/v1/jobs/search", params={"start": 1}, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["recordsFiltered"] == total - 1
    assert result["recordsTotal"] == total

    # Ask for specific length
    response = client.get("/v1/jobs/search", params={"length": 3}, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["recordsFiltered"] == 3
    assert result["recordsTotal"] == total
