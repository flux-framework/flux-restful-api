import base64
import os
import sys
import time

from fastapi.testclient import TestClient

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)

sys.path.insert(0, root)

# Define authentication in environment for server
flux_user = "fluxuser"
flux_token = "12345"
os.environ["FLUX_USER"] = flux_user
os.environ["FLUX_TOKEN"] = flux_token
os.environ["FLUX_REQUIRE_AUTH"] = "true"


from app.main import app  # noqa

client = TestClient(app)


def get_basic_auth(username, password):
    auth_str = "%s:%s" % (username, password)
    return base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")


def get_headers():
    auth_header = get_basic_auth(flux_user, flux_token)
    if isinstance(auth_header, bytes):
        auth_header = auth_header.decode("utf-8")
    return {"Authorization": "Basic %s" % auth_header}


def test_submit_list_job():

    # No jobs are submit!
    response = client.get("/jobs")
    assert response.status_code == 401
    assert "www-authenticate" in response.headers

    headers = get_headers()
    response = client.get("/jobs", headers=headers)
    assert response.status_code == 200

    # Now submit a job, ensure we get one job back
    response = client.post("/jobs/submit", json={"command": "sleep 5"}, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert "id" in result
    jobid = result["id"]

    response = client.get("/jobs", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert "jobs" in result
    result = result["jobs"]
    assert len(result) == 1
    assert result[0]["id"] == jobid


def test_cancel_job():

    headers = get_headers()

    # Now submit a job, ensure we get one job back
    response = client.post(
        "/jobs/submit", json={"command": "sleep 10"}, headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    jobid = result["id"]
    response = client.post(f"/jobs/{jobid}/cancel", headers=headers)
    assert response.status_code == 200
    # TODO we don't have way to actually verify this!


def test_job_output():

    # Now submit a job, ensure we get one job back
    headers = get_headers()

    response = client.post(
        "/jobs/submit", json={"command": "echo pancakes 🥞️🥞️🥞️"}, headers=headers
    )
    assert response.status_code == 200
    result = response.json()
    jobid = result["id"]
    res = client.get(f"/jobs/{jobid}/output", headers=headers)
    assert response.status_code == 200
    lines = res.json()

    # First try, we won't have output yet
    assert "Message" in lines
    time.sleep(3)

    # Try again - we should have it after a sleep
    res = client.get(f"/jobs/{jobid}/output", headers=headers)
    assert response.status_code == 200
    lines = res.json()
    assert "Output" in lines
    assert "pancakes 🥞️🥞️🥞️\n" in lines["Output"]
