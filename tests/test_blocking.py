"""
Requests about a running job must not block (need a running Flux instance).

Before this, reading a running job's output or opening its page watched the
job's eventlog and returned only when the job ended, holding the event loop
and with it every other request.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

LIMIT = 5  # seconds; a blocked request would take the job's full runtime


@pytest.fixture
def running_job(client, use_backend):
    use_backend("none")
    response = client.post(
        "/v1/jobs/submit",
        params={"command": "sh -c 'echo first; sleep 90; echo second'"},
    )
    assert response.status_code == 200
    jobid = response.json()["id"]
    yield jobid
    client.post(f"/v1/jobs/{jobid}/cancel")


def timed(fn):
    start = time.time()
    result = fn()
    return result, time.time() - start


def wait_for_output(client, jobid, needle, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response, elapsed = timed(lambda: client.get(f"/v1/jobs/{jobid}/output"))
        assert elapsed < LIMIT, "output request blocked on a running job"
        if needle in "".join(response.json().get("Output") or []):
            return response
        time.sleep(0.5)
    raise AssertionError(f"{needle!r} never appeared in the output")


def test_output_of_running_job_is_a_snapshot(client, running_job):
    response = wait_for_output(client, running_job, "first")
    output = "".join(response.json()["Output"])
    assert "first" in output
    assert "second" not in output  # the job is still running


def test_job_page_of_running_job_returns_promptly(client, running_job):
    wait_for_output(client, running_job, "first")
    response, elapsed = timed(lambda: client.get(f"/job/{running_job}"))
    assert response.status_code == 200
    assert elapsed < LIMIT
    assert "first" in response.text


def test_running_job_does_not_block_other_requests(client, running_job):
    wait_for_output(client, running_job, "first")
    paths = [f"/v1/jobs/{running_job}/output"] * 8 + ["/v1/auth", "/v1/jobs", "/"] * 4
    with ThreadPoolExecutor(max_workers=len(paths)) as pool:
        start = time.time()
        results = list(pool.map(lambda p: client.get(p).status_code, paths))
        elapsed = time.time() - start
    assert results == [200] * len(paths)
    assert elapsed < LIMIT


def test_stream_delivers_output_before_the_job_ends(client, running_job, live_server):
    """
    Through a real server: the test client cannot observe a response before
    the whole ASGI call has finished.
    """
    import httpx

    wait_for_output(client, running_job, "first")
    start = time.time()
    with httpx.stream(
        "GET", f"{live_server}/v1/jobs/{running_job}/output/stream", timeout=LIMIT
    ) as response:
        assert response.status_code == 200
        first_chunk = next(response.iter_text())
    assert "first" in first_chunk
    assert time.time() - start < LIMIT


def test_bad_and_missing_job_ids(client, use_backend):
    use_backend("none")
    for path in ["/v1/jobs/notanid", "/v1/jobs/notanid/output", "/job/notanid"]:
        response = client.get(path)
        assert response.status_code == 400, path
        assert "not a valid job id" in response.json()["detail"]
    assert client.post("/v1/jobs/notanid/cancel").status_code == 400
    assert client.get("/v1/jobs/999999999999").status_code == 404
    assert client.get("/job/999999999999").status_code == 404
    # Non-numeric paging parameters are ignored rather than a 500
    assert (
        client.get(
            "/v1/jobs/search", params={"start": "abc", "length": "x"}
        ).status_code
        == 200
    )


def test_many_quiet_streams_do_not_starve_the_server(client, running_job, live_server):
    """
    Each open stream is advanced in the thread pool. If a step blocked until
    the job printed something, a quiet job would pin one pool thread per
    stream, and about 40 streams (the pool size) froze every other request.
    """
    import threading

    import httpx

    wait_for_output(client, running_job, "first")
    stop = threading.Event()

    def hold_stream():
        try:
            with httpx.stream(
                "GET", f"{live_server}/v1/jobs/{running_job}/output/stream", timeout=30
            ) as response:
                for _ in response.iter_raw():
                    if stop.is_set():
                        break
        except Exception:
            pass

    threads = [threading.Thread(target=hold_stream, daemon=True) for _ in range(45)]
    for t in threads:
        t.start()
    time.sleep(2)  # let every stream reach its wait
    try:
        start = time.time()
        response = httpx.get(f"{live_server}/v1/jobs", timeout=LIMIT)
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < LIMIT
    finally:
        stop.set()


def test_stream_opened_before_the_job_starts(client, use_backend, live_server):
    """
    A stream opened right after submit, before the job has started (or while
    it queues behind other jobs), must still deliver the job's output.
    """
    import httpx

    use_backend("none")
    for _ in range(5):
        response = client.post("/v1/jobs/submit", params={"command": "echo hello"})
        assert response.status_code == 200
        jobid = response.json()["id"]
        with httpx.stream(
            "GET", f"{live_server}/v1/jobs/{jobid}/output/stream", timeout=120
        ) as stream:
            assert stream.status_code == 200
            body = "".join(stream.iter_text())
        assert "hello" in body, body
