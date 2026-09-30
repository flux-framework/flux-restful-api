"""
Integration tests for authentication through the HTTP API and web views.

These need a running Flux instance (run under `flux start`).
"""

from datetime import timedelta

import pytest
from conftest import oidc_token, unprivileged_user
from jose import jwt

import app.auth as auth
from app.auth import tokens

SECRET = "shared-with-clients"


def handshake_header(user, password, secret=SECRET, scope="token"):
    payload = {"user": user, "pass": password, "scope": scope}
    return {"Authorization": "Bearer " + jwt.encode(payload, secret, algorithm="HS256")}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_none_backend_is_anonymous(client, use_backend):
    use_backend("none")
    assert client.get("/v1/auth").json()["backend"] == "none"
    assert client.get("/v1/jobs").status_code == 200
    assert client.get("/jobs").status_code == 200

    # Nobody can be a superuser, so the service cannot be stopped remotely
    assert client.post("/v1/service/stop").status_code == 403


def test_database_backend_api(client, db, use_backend, make_user):
    use_backend("database", secret_key=None)
    make_user("alice", "wonderland")

    response = client.get("/v1/jobs")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    # Every job endpoint, including the stream, requires a token
    assert client.get("/v1/jobs/1234/output/stream").status_code == 401
    assert client.get("/v1/nodes").status_code == 401
    assert client.post("/v1/jobs/submit", params={"command": "true"}).status_code == 401

    # The handshake is off without a shared secret
    response = client.post("/v1/token", headers=handshake_header("alice", "wonderland"))
    assert response.status_code == 400

    # OAuth2 password form login works
    # A bad password is 400 (OAuth2 invalid_grant), never 401
    response = client.post(
        "/v1/login/access-token", data={"username": "alice", "password": "nope"}
    )
    assert response.status_code == 400
    response = client.post(
        "/v1/login/access-token", data={"username": "alice", "password": "wonderland"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    assert client.get("/v1/jobs", headers=bearer(token)).status_code == 200
    assert client.get("/v1/jobs", headers=bearer(token + "x")).status_code == 401


def test_shared_secret_handshake(client, db, use_backend, make_user):
    use_backend("shared-secret", secret_key=SECRET)
    make_user("alice", "wonderland")
    assert client.get("/v1/auth").json()["shared_secret_handshake"] is True

    response = client.post("/v1/token", headers=handshake_header("alice", "wonderland"))
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    token = body["access_token"]
    assert client.get("/v1/jobs", headers=bearer(token)).status_code == 200

    # Failures are 400, never 401: a 401 would tell the client to request a
    # token, which is what just failed, and it would loop forever
    for headers in [
        {},
        {"Authorization": "Bearer garbage"},
        handshake_header("alice", "wrong"),
        handshake_header("nobody", "wonderland"),
        handshake_header("alice", "wonderland", secret="wrong-secret"),
        handshake_header("alice", "wonderland", scope="admin"),
    ]:
        response = client.post("/v1/token", headers=headers)
        assert response.status_code == 400, headers
        assert "www-authenticate" not in response.headers


def test_shared_secret_cannot_forge_access_tokens(client, db, use_backend, make_user):
    """
    Knowing the client-facing shared secret must not let anyone mint tokens.
    """
    use_backend("shared-secret", secret_key=SECRET)
    make_user("alice", "wonderland")
    make_user("root", "toor", superuser=True)

    forged = jwt.encode(
        {"sub": "root", "backend": "shared-secret", "exp": 4102444800},
        SECRET,
        algorithm="HS256",
    )
    assert client.get("/v1/jobs", headers=bearer(forged)).status_code == 401
    assert client.post("/v1/service/stop", headers=bearer(forged)).status_code == 401


def test_expired_token_returns_401_with_challenge(client, db, use_backend, make_user):
    """
    The Python client re-authenticates on 401 + WWW-Authenticate, so an
    expired token must not come back as a bare 403.
    """
    use_backend("database")
    make_user("alice", "wonderland")
    expired = tokens.create_access_token(
        "alice", backend="database", expires_delta=timedelta(minutes=-1)
    )
    response = client.get("/v1/jobs", headers=bearer(expired))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_superuser_required_for_service_stop(client, db, use_backend, make_user):
    use_backend("database")
    make_user("alice", "wonderland")
    token = auth.get_backend().issue_token(
        auth.get_backend().authenticate(db, "alice", "wonderland")
    )
    response = client.post("/v1/service/stop", headers=bearer(token))
    assert response.status_code == 403


def test_views_basic_auth(client, db, use_backend, make_user):
    use_backend("database")
    make_user("alice", "wonderland")

    response = client.get("/jobs")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"

    assert client.get("/jobs", auth=("alice", "wrong")).status_code == 401
    assert client.get("/jobs", auth=("alice", "wonderland")).status_code == 200
    assert client.get("/page/about", auth=("alice", "wonderland")).status_code == 200

    # A bearer token also works for the views
    token = auth.get_backend().issue_token(
        auth.get_backend().authenticate(db, "alice", "wonderland")
    )
    assert client.get("/jobs", headers=bearer(token)).status_code == 200

    # The home page never requires auth
    assert client.get("/").status_code == 200


def test_oidc_backend_api(client, db, use_backend, rsa_keypair):
    pem, public_jwk = rsa_keypair
    use_backend(
        "oidc", oidc_issuer="https://issuer.example.com", oidc_audience="flux-restful"
    )
    auth.get_backend()._jwks_loader = lambda: {"keys": [public_jwk]}

    info = client.get("/v1/auth").json()
    assert info["backend"] == "oidc"
    assert info["password_login"] is False
    assert info["oidc"]["issuer"] == "https://issuer.example.com"

    # No password login or handshake
    response = client.post(
        "/v1/login/access-token", data={"username": "alice", "password": "x"}
    )
    assert response.status_code == 400
    assert (
        client.post("/v1/token", headers=handshake_header("a", "b")).status_code == 400
    )

    token = oidc_token(pem)
    assert client.get("/v1/jobs").status_code == 401
    assert client.get("/v1/jobs", headers=bearer(token)).status_code == 200
    assert (
        client.get("/v1/jobs", headers=bearer(oidc_token(pem, aud="x"))).status_code
        == 401
    )

    # Views: basic auth is not possible, a bearer header is
    response = client.get("/jobs", auth=("alice", "x"))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert client.get("/jobs", headers=bearer(token)).status_code == 200


def test_multi_user_mode_requires_a_system_account(client, db, use_backend, make_user):
    """
    Whatever the backend says, in multi-user mode the server becomes the
    user to run their jobs, so every principal must be a real, unprivileged
    system account.
    """
    use_backend("database", flux_server_mode="multi-user")
    me = unprivileged_user()
    if me is None:
        pytest.skip("needs an unprivileged system account")
    make_user(me, "mypassword")
    make_user("alice", "wonderland")  # no such system account
    make_user("daemon", "daemon")  # privileged system account

    backend = auth.get_backend()

    def token(user, password):
        return bearer(backend.issue_token(backend.authenticate(db, user, password)))

    assert client.get("/v1/jobs", headers=token(me, "mypassword")).status_code == 200
    for user, password in [("alice", "wonderland"), ("daemon", "daemon")]:
        response = client.get("/v1/jobs", headers=token(user, password))
        assert response.status_code == 403, user
        assert "not an allowed system account" in response.json()["detail"]
        # The web views apply the same rule
        assert client.get("/jobs", auth=(user, password)).status_code == 403
