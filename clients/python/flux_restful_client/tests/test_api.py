import time

from flux_restful_client.main import get_client


def test_list_nodes():
    """
    Test listing nodes
    """
    client = get_client()
    response = client.list_nodes()
    assert "nodes" in response
    assert response["nodes"]
    assert len(response["nodes"]) == 1


def test_submit_list_job():
    """
    Test a manual submission
    """
    client = get_client()

    # No jobs are submit!
    response = client.jobs()
    assert isinstance(response, dict)
    assert "jobs" in response
    assert not response["jobs"]

    # Now submit a job, ensure we get one job back
    response = client.submit("sleep 5")
    assert isinstance(response, dict)
    for key in ["Message", "id"]:
        assert key in response
    jobid = response["id"]

    # Now we should see jobs
    response = client.jobs()
    assert response["jobs"]
    assert len(response["jobs"]) == 1
    assert response["jobs"][0]["id"] == jobid


def test_cancel_job():
    client = get_client()
    response = client.submit("sleep 10")
    jobid = response["id"]
    response = client.cancel(jobid)
    assert "Message" in response
    assert "requested to cancel" in response["Message"]

    # Give time to cancel
    time.sleep(3)
    response = client.cancel(jobid)
    assert "Message" in response
    assert "cannot be cancelled" in response["Message"]
