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


def test_job_output():
    """
    Test endpoint to retrieve list of job output
    """
    client = get_client()

    # Now submit a job, ensure we get one job back
    result = client.submit("echo pancakes 🥞️🥞️🥞️")
    jobid = result["id"]
    lines = client.output(jobid)

    # First try, often we won't have output yet
    if "Message" in lines:
        assert "not exist yet" in lines["Message"]
    time.sleep(3)

    # Try again - we should have it after a sleep
    lines = client.output(jobid)
    assert "Output" in lines
    assert "pancakes 🥞️🥞️🥞️\n" in lines["Output"]


def test_job_query():
    """
    Test endpoint to query jobs
    """
    client = get_client()

    # Submit 5 jobs
    for _ in range(5):
        client.submit("sleep 1")
    result = client.search()

    for key in ["recordsTotal", "recordsFiltered", "draw", "data"]:
        assert key in result

    total = result["recordsTotal"]
    assert len(result["data"]) == total

    # Ask to start at 2 (should be one less record)
    result = client.search(start=1)
    assert result["recordsFiltered"] == total - 1
    assert result["recordsTotal"] == total

    # Ask for specific length
    result = client.search(start=1, length=3)
    assert result["recordsFiltered"] == 3
    assert result["recordsTotal"] == total
