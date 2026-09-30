"""
Run the real Python client against the app (through the test client session).

These need a running Flux instance (run under `flux start`).
"""

import os
import sys

import pytest

# Test the client in this checkout, not a copy that happens to be installed
here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(here), "clients", "python"))

from flux_restful_client.main import get_client  # noqa: E402

SECRET = "shared-with-clients"


@pytest.fixture
def make_client(client, use_backend, make_user):
    use_backend("shared-secret", secret_key=SECRET)
    make_user("alice", "wonderland")

    def _make(user, token):
        cli = get_client(
            host="http://testserver", user=user, token=token, secret_key=SECRET
        )
        # The client uses an httpx session, which the test client is
        cli.session = client
        # Count requests to the token endpoint
        calls = []
        original = cli.do_request

        def counting(endpoint, *args, **kwargs):
            calls.append(endpoint)
            return original(endpoint, *args, **kwargs)

        cli.do_request = counting
        cli.calls = calls
        return cli

    return _make


def test_client_authenticates_with_correct_password(make_client):
    cli = make_client("alice", "wonderland")
    response = cli.jobs()
    assert "jobs" in response
    assert cli.calls.count("token") == 1
    # The token is reused for later requests
    cli.jobs()
    assert cli.calls.count("token") == 1


@pytest.mark.parametrize("user,token", [("alice", "wrong"), ("nobody", "wonderland")])
def test_client_does_not_loop_on_bad_credentials(make_client, user, token):
    cli = make_client(user, token)
    response = cli.do_request("jobs")
    assert response.status_code == 401
    assert cli.calls.count("token") == 1
