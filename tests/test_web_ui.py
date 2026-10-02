"""
Integration tests for the web UI: output escaping, CSRF, and page lookup.

These need a running Flux instance (run under `flux start`).
"""

import time

import pytest
from fastapi import HTTPException

from flux_restful.library import helpers
from flux_restful.library.csrf import COOKIE


def submit_via_api(client, command):
    response = client.post("/v1/jobs/submit", params={"command": command})
    assert response.status_code == 200
    return response.json()["id"]


def wait_for_output(client, jobid, needle, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        lines = client.get(f"/v1/jobs/{jobid}/output").json().get("Output") or []
        text = "".join(lines)
        if needle in text:
            return text
        time.sleep(0.5)
    raise AssertionError(f"{needle!r} not found in job {jobid} output")


def test_job_environment_excludes_server_secrets(client, use_backend, monkeypatch):
    use_backend("none")
    monkeypatch.setenv("FLUX_TOKEN", "server-password-do-not-leak")
    monkeypatch.setenv("FLUX_SECRET_KEY", "shared-secret-do-not-leak")
    response = client.post(
        "/v1/jobs/submit",
        params={"command": "sh -c env"},
        json={"PANCAKES": "yes"},
    )
    assert response.status_code == 200
    text = wait_for_output(client, response.json()["id"], "PANCAKES=yes")
    assert "PATH=" in text
    assert "do-not-leak" not in text
    assert "FLUX_TOKEN=" not in text
    assert "FLUX_SECRET_KEY=" not in text
    assert "FLUX_TOKEN_SIGNING_KEY=" not in text


def test_flux_commands_work_inside_jobs(client, use_backend):
    use_backend("none")
    jobid = submit_via_api(client, "flux getattr size")
    text = wait_for_output(client, jobid, "1")
    assert text.strip().isdigit()


def test_submit_form_requires_csrf_token(client, use_backend):
    use_backend("none")
    client.cookies.clear()
    response = client.get("/jobs/submit")
    assert response.status_code == 200
    token = client.cookies.get(COOKIE)
    assert token
    assert f'name="csrf_token" value="{token}"' in response.text

    # Cross-site form post: no token
    assert client.post("/jobs/submit", data={"command": "sleep 1"}).status_code == 403
    assert (
        client.post(
            "/jobs/submit", data={"command": "sleep 1", "csrf_token": "x"}
        ).status_code
        == 403
    )

    response = client.post(
        "/jobs/submit", data={"command": "sleep 1", "csrf_token": token}
    )
    assert response.status_code == 200
    assert "successfully submit" in response.text


def test_cancel_is_a_csrf_protected_post(client, use_backend):
    use_backend("none")
    jobid = submit_via_api(client, "sleep 60")
    client.get("/jobs/submit")
    token = client.cookies.get(COOKIE)

    # A link or image cannot cancel a job any more
    assert client.get(f"/job/{jobid}/cancel").status_code == 405
    assert client.post(f"/job/{jobid}/cancel").status_code == 403

    response = client.post(
        f"/job/{jobid}/cancel", data={"csrf_token": token}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith(f"/job/{jobid}?msg=")
    assert client.get(response.headers["location"]).status_code == 200


def test_job_page_escapes_reflected_message(client, use_backend):
    use_backend("none")
    jobid = submit_via_api(client, "sleep 60")
    payload = "<script>alert('xss')</script>"
    response = client.get(f"/job/{jobid}", params={"msg": payload})
    assert response.status_code == 200
    assert payload not in response.text
    assert "&lt;script&gt;" in response.text

    # Unknown job ids are a 404, not a crash
    assert client.get("/job/999999999999").status_code == 404


def test_jobs_table_renders_cells_as_text(client, use_backend):
    use_backend("none")
    response = client.get("/jobs")
    assert response.status_code == 200
    assert "render.text()" in response.text
    assert "escapeHtml(" in response.text


def test_pages(client, use_backend):
    use_backend("none")
    assert client.get("/page/about").status_code == 200
    assert client.get("/page/nope").status_code == 404
    assert client.get("/page/about.md").status_code == 404

    # Page names are validated before touching the filesystem (the HTTP client
    # normalizes dot segments away, so exercise the helper directly)
    assert helpers.get_page("about.md")["text"]
    for name in ["..", "../about.md", "..%2F..%2Fetc%2Fpasswd.md", "nope.md", ""]:
        with pytest.raises(HTTPException) as info:
            helpers.get_page(name)
        assert info.value.status_code == 404
