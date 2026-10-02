import base64
import os
import sys
import time

from fastapi.testclient import TestClient

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)

sys.path.insert(0, root)

from jose import jwt  # noqa

from app.main import app  # noqa

client = TestClient(app)

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)

sys.path.insert(0, root)


def get_basic_auth(username, password):
    auth_str = "%s:%s" % (username, password)
    return base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")


def get_headers():
    """
    Prepare JWT encoded header.

    This is encoded with the shared user/server secret
    """
    flux_user = os.environ.get("FLUX_USER")
    flux_token = os.environ.get("FLUX_TOKEN")
    secret_key = os.environ.get("FLUX_SECRET_KEY")
    print(flux_user)
    print(flux_token)
    print(secret_key)
    if not secret_key:
        sys.exit("Cannot generate header without secret key")
    auth_str = {"user": flux_user, "pass": flux_token, "scope": "token"}
    encoded = jwt.encode(auth_str, secret_key)  # algorithm is 'HS256'
    return {"Authorization": f"Bearer {encoded}"}


# Do we want auth?
access_token = None
test_auth = False
headers = {}

if os.environ.get("TEST_AUTH"):
    test_auth = True


def authenticate(endpoint, method="get", json=None, params=None, expected_status=200):
    global access_token

    if method == "get":
        response = client.get(endpoint, params=params)
    else:
        response = client.post(endpoint, json=json, params=params)

    print(response.json())
    if test_auth and not access_token and response.status_code != 401:
        raise ValueError(f"{endpoint} with auth enabled should return 401")

    # We should only have to get once and reuse
    if test_auth and not access_token:
        if "www-authenticate" not in response.headers:
            raise ValueError(f"{endpoint} missing www-authenticate header.")

        response = client.post("/v1/token", headers=get_headers())
        assert response.status_code == 200
        token = response.json()
        assert "access_token" in token and "token_type" in token
        access_token = token["access_token"]

    # Redo the request with the token
    if test_auth:
        if method == "get":
            response = client.get(
                endpoint,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        else:
            response = client.post(
                endpoint,
                json=json,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )

    assert response.status_code == expected_status
    return response


def test_token_endpoint_rejects_malformed_header():
    """
    A garbage bearer token on the token endpoint is denied, not a 500.
    """
    import app.auth as auth

    response = client.post("/v1/token", headers={"Authorization": "Bearer not-a-jwt"})
    if auth.handshake_enabled():
        # Handshake on: an undecodable payload is a failed login, which is 400
        # and never 401 (a 401 would tell clients to go fetch a token)
        assert response.status_code == 400
        assert "www-authenticate" not in response.headers
    else:
        # Handshake off (no shared secret or no password backend): disabled
        assert response.status_code == 400
        assert "not enabled" in response.json()["detail"]


def test_submit_list_job():
    """
    Test a manual submission
    """
    # No jobs are submit!
    response = authenticate("/v1/jobs")

    assert not response.json()["jobs"]

    # Now submit a job, ensure we get one job back
    response = authenticate(
        "/v1/jobs/submit", method="post", params={"command": "sleep 5"}
    )
    result = response.json()
    assert "id" in result
    jobid = result["id"]

    # List jobs with and without details
    response = authenticate("/v1/jobs")
    result = response.json()
    assert "jobs" in result
    result = result["jobs"]
    assert len(result) == 1
    assert result[0]["id"] == jobid

    response = authenticate("/v1/jobs", params={"details": True})
    result = response.json()

    assert str(jobid) in result
    result = result[str(jobid)]
    assert len(result) > 20
    assert result["id"] == jobid

    # Testing asking for a listing
    response = authenticate("/v1/jobs", params={"details": True, "listing": True})
    result = response.json()
    assert isinstance(result, list)
    assert result[0]["id"] == jobid

    # And setting an integer limit (only relevant for details)
    response = authenticate("/v1/jobs", params={"limit": 0, "details": True})
    result = response.json()
    assert not result


def test_cancel_job():
    # Now submit a job, ensure we get one job back
    response = authenticate(
        "/v1/jobs/submit", method="post", params={"command": "sleep 10"}
    )
    result = response.json()
    jobid = result["id"]
    response = authenticate(f"/v1/jobs/{jobid}/cancel", method="post")
    # TODO we don't have way to actually verify that cancel happened


def test_submit_option_flags():
    """
    Test that option flags are parsed.

    We used to validate option flags, but flux changes and this is not reasonable to do.
    """
    # Valid
    response = authenticate(
        "/v1/jobs/submit",
        method="post",
        params={"command": "sleep 1", "option_flags": "ompi=openmpi@5"},
    )
    result = response.json()
    assert "id" in result


def test_job_output():
    """
    Test endpoint to retrieve list of job output
    """
    # Now submit a job, ensure we get one job back
    response = authenticate(
        "/v1/jobs/submit", method="post", params={"command": "echo pancakes 🥞️🥞️🥞️"}
    )
    result = response.json()
    jobid = result["id"]
    res = authenticate(f"/v1/jobs/{jobid}/output")
    lines = res.json()

    # First try, often we won't have output yet
    if "Message" in lines:
        assert "not exist yet" in lines["Message"]
    # Wait for the job to finish (on a small machine it may queue behind
    # the sleep jobs earlier tests submitted) rather than sleeping a fixed time
    deadline = time.time() + 120
    while time.time() < deadline:
        if authenticate(f"/v1/jobs/{jobid}").json()["state"] == "INACTIVE":
            break
        time.sleep(0.5)

    # Now we should have it
    res = authenticate(f"/v1/jobs/{jobid}/output")
    lines = res.json()
    assert "Output" in lines
    assert "pancakes 🥞️🥞️🥞️\n" in lines["Output"]


def test_job_query():
    """
    Test endpoint to query jobs
    """
    # Submit 5 jobs
    for _ in range(5):
        authenticate("/v1/jobs/submit", method="post", params={"command": "sleep 1"})
    response = authenticate("/v1/jobs/search")
    result = response.json()

    for key in ["recordsTotal", "recordsFiltered", "draw", "data"]:
        assert key in result
    total = result["recordsTotal"]
    assert len(result["data"]) == total

    # Ask to start at 2 (should be one less record)
    response = authenticate("/v1/jobs/search", params={"start": 1})
    result = response.json()
    assert result["recordsFiltered"] == total - 1
    assert result["recordsTotal"] == total

    # Ask for specific length
    response = authenticate("/v1/jobs/search", params={"length": 3})
    result = response.json()
    assert result["recordsFiltered"] == 3
    assert result["recordsTotal"] == total
