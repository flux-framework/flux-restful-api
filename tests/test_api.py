import os
import sys
import time

from fastapi.testclient import TestClient

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)

sys.path.insert(0, root)

from app.main import app  # noqa

client = TestClient(app)


def test_submit_list_job():
    """
    Test a manual submission
    """
    # No jobs are submit!
    response = client.get("/jobs")
    assert response.status_code == 200
    assert not response.json()["jobs"]

    # Now submit a job, ensure we get one job back
    response = client.post("/jobs/submit", json={"command": "sleep 5"})
    assert response.status_code == 200
    result = response.json()
    assert "id" in result
    jobid = result["id"]

    response = client.get("/jobs")
    assert response.status_code == 200
    result = response.json()
    assert "jobs" in result
    result = result["jobs"]
    assert len(result) == 1
    assert result[0]["id"] == jobid


def test_cancel_job():

    # Now submit a job, ensure we get one job back
    response = client.post("/jobs/submit", json={"command": "sleep 10"})
    assert response.status_code == 200
    result = response.json()
    jobid = result["id"]
    response = client.post(f"/jobs/{jobid}/cancel")
    assert response.status_code == 200
    # TODO we don't have way to actually verify this!


def test_job_output():

    # Now submit a job, ensure we get one job back
    response = client.post("/jobs/submit", json={"command": "echo pancakes 🥞️🥞️🥞️"})
    assert response.status_code == 200
    result = response.json()
    jobid = result["id"]
    res = client.get(f"/jobs/{jobid}/output")
    assert response.status_code == 200
    lines = res.json()

    # First try, we won't have output yet
    assert "Message" in lines
    time.sleep(3)

    # Try again - we should have it after a sleep
    res = client.get(f"/jobs/{jobid}/output")
    assert response.status_code == 200
    lines = res.json()
    assert "Output" in lines
    assert "pancakes 🥞️🥞️🥞️\n" in lines["Output"]
