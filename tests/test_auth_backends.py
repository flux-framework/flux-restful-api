"""
Unit tests for the auth backends. These do not need a Flux instance.
"""

import os
import sys
import time
from datetime import timedelta

import pytest
from conftest import make_rsa_keypair, oidc_token, unprivileged_user
from jose import jwt

import flux_restful.auth as auth
from flux_restful.auth import tokens
from flux_restful.auth.base import AuthError
from flux_restful.auth.oidc import JWKS_REFRESH_MIN_SECONDS, OidcBackend
from flux_restful.auth.pam import PamBackend
from flux_restful.core import config
from flux_restful.core.config import settings

OIDC_SETTINGS = {
    "oidc_issuer": "https://issuer.example.com",
    "oidc_audience": "flux-restful",
}


class FakePam:
    def __init__(self, accept):
        self.accept = accept
        self.calls = []

    def authenticate(self, username, password, service=None):
        self.calls.append((username, password, service))
        return (username, password) in self.accept


def test_config_bool_envar(monkeypatch):
    for value, expected in [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("", False),
    ]:
        monkeypatch.setenv("FLUX_TEST_BOOL", value)
        assert config.get_bool_envar("FLUX_TEST_BOOL") is expected
    monkeypatch.delenv("FLUX_TEST_BOOL")
    assert config.get_bool_envar("FLUX_TEST_BOOL", default=True) is True


def test_config_auth_backend_selection(monkeypatch):
    monkeypatch.delenv("FLUX_AUTH_BACKEND", raising=False)
    monkeypatch.delenv("FLUX_REQUIRE_AUTH", raising=False)
    assert config.get_auth_backend() == "none"

    # Backwards compatibility with the old flag
    monkeypatch.setenv("FLUX_REQUIRE_AUTH", "true")
    assert config.get_auth_backend() == "shared-secret"
    monkeypatch.setenv("FLUX_REQUIRE_AUTH", "false")
    assert config.get_auth_backend() == "none"

    monkeypatch.setenv("FLUX_AUTH_BACKEND", "PAM")
    assert config.get_auth_backend() == "pam"
    monkeypatch.setenv("FLUX_AUTH_BACKEND", "ldap")
    with pytest.raises(ValueError):
        config.get_auth_backend()


def test_unknown_backend():
    with pytest.raises(AuthError):
        auth.create_backend("ldap")


def test_none_backend(db, use_backend):
    backend = use_backend("none")
    assert backend.name == "none"
    assert backend.supports_password is False
    assert backend.authenticate(db, "anyone", "anything") is None
    assert backend.verify_token(db, "whatever") is None
    assert auth.handshake_enabled() is False
    assert auth.describe()["backend"] == "none"


def test_database_backend_authenticate(db, use_backend, make_user):
    backend = use_backend("database", secret_key=None)
    make_user("alice", "wonderland")
    make_user("root", "toor", superuser=True)
    make_user("gone", "gone", active=False)

    principal = backend.authenticate(db, "alice", "wonderland")
    assert principal is not None
    assert principal.user_name == "alice"
    assert principal.is_superuser is False
    assert principal.backend == "database"

    assert backend.authenticate(db, "root", "toor").is_superuser is True
    assert backend.authenticate(db, "alice", "wrong") is None
    assert backend.authenticate(db, "nobody", "wonderland") is None
    assert backend.authenticate(db, "gone", "gone") is None
    assert backend.authenticate(db, "", "") is None

    # Without a secret the client handshake is off, password login is on
    assert auth.handshake_enabled() is False
    assert backend.supports_password is True


def test_database_backend_admin_users(db, use_backend, make_user):
    backend = use_backend("database", admin_users=["alice"])
    make_user("alice", "wonderland")
    assert backend.authenticate(db, "alice", "wonderland").is_superuser is True


def test_database_tokens_roundtrip(db, use_backend, make_user):
    backend = use_backend("database")
    make_user("alice", "wonderland")
    principal = backend.authenticate(db, "alice", "wonderland")

    token = backend.issue_token(principal)
    resolved = backend.verify_token(db, token)
    assert resolved is not None and resolved.user_name == "alice"

    # Deactivating the user invalidates their outstanding tokens
    make_user("alice", "wonderland", active=False)
    assert backend.verify_token(db, token) is None


def test_tokens_reject_expired_tampered_and_foreign(db, use_backend, make_user):
    backend = use_backend("database", secret_key="shared-with-clients")
    make_user("alice", "wonderland")

    expired = tokens.create_access_token(
        "alice", backend="database", expires_delta=timedelta(minutes=-1)
    )
    assert backend.verify_token(db, expired) is None

    # Signed with the client-facing shared secret: must never be accepted
    forged = jwt.encode(
        {"sub": "alice", "backend": "database", "exp": 4102444800},
        settings.secret_key,
        algorithm="HS256",
    )
    assert backend.verify_token(db, forged) is None

    # Signed correctly but for a different backend
    other = tokens.create_access_token("alice", backend="pam")
    assert backend.verify_token(db, other) is None

    assert backend.verify_token(db, "not.a.token") is None
    assert backend.verify_token(db, "") is None


def test_token_issuing_backends_require_signing_key(use_backend):
    for name in ["database", "shared-secret", "pam"]:
        with pytest.raises(AuthError, match="FLUX_TOKEN_SIGNING_KEY"):
            use_backend(name, secret_key="s", token_signing_key=None)
    # Backends that never issue tokens do not need it
    use_backend("none", token_signing_key=None)


def test_shared_secret_backend_requires_secret(use_backend):
    with pytest.raises(AuthError):
        use_backend("shared-secret", secret_key=None)
    backend = use_backend("shared-secret", secret_key="notsecrethoo")
    assert backend.name == "shared-secret"
    assert auth.handshake_enabled() is True
    assert auth.describe()["shared_secret_handshake"] is True


def test_pam_backend(db, monkeypatch):
    me = unprivileged_user()
    if me is None:
        pytest.skip("needs an unprivileged system account")
    fake = FakePam(accept={(me, "correct")})
    # python-pam is not required to run the tests, so bypass create_backend()
    # and construct the backend with a fake authenticator.
    monkeypatch.setattr(settings, "admin_users", [me])
    monkeypatch.setattr(settings, "pam_service", "flux-restful")
    monkeypatch.setattr(settings, "token_signing_key", "signing-key-for-tests")
    backend = PamBackend(authenticator=fake)

    principal = backend.authenticate(db, me, "correct")
    assert principal is not None
    assert principal.user_name == me
    assert principal.is_superuser is True
    assert principal.backend == "pam"
    assert fake.calls[-1] == (me, "correct", "flux-restful")

    assert backend.authenticate(db, me, "wrong") is None
    assert backend.authenticate(db, me, "") is None

    # PAM says yes but the account does not exist on this host
    fake.accept.add(("no-such-user-xyz", "pw"))
    assert backend.authenticate(db, "no-such-user-xyz", "pw") is None

    token = backend.issue_token(principal)
    assert backend.verify_token(db, token).user_name == me


def test_pam_backend_warns_when_not_root(db, monkeypatch, caplog):
    monkeypatch.setattr(os, "getuid", lambda: 1000)
    PamBackend(authenticator=FakePam(accept=set())).validate()
    assert "root" in caplog.text


def test_pam_backend_requires_python_pam(use_backend, monkeypatch):
    monkeypatch.setitem(sys.modules, "pam", None)
    with pytest.raises(AuthError):
        use_backend("pam")


def test_oidc_backend_requires_settings(use_backend):
    with pytest.raises(AuthError):
        use_backend("oidc", oidc_issuer=None, oidc_audience=None)


def test_oidc_backend_verifies_provider_tokens(db, use_backend, rsa_keypair):
    pem, public_jwk = rsa_keypair
    use_backend("oidc", admin_users=["alice"], **OIDC_SETTINGS)
    backend = OidcBackend(jwks_loader=lambda: {"keys": [public_jwk]})

    # The identity is the subject, not a display name the user may choose
    principal = backend.verify_token(db, oidc_token(pem))
    assert principal is not None
    assert principal.user_name == "alice"
    assert principal.is_superuser is True
    assert principal.backend == "oidc"
    mallory = backend.verify_token(
        db, oidc_token(pem, sub="mallory-id", preferred_username="alice")
    )
    assert mallory.user_name == "mallory-id"
    assert mallory.is_superuser is False
    assert backend.verify_token(db, oidc_token(pem, sub=None)) is None
    assert backend.verify_token(db, oidc_token(pem, sub=["not", "a", "string"])) is None

    assert backend.verify_token(db, oidc_token(pem, aud="other-app")) is None
    assert (
        backend.verify_token(db, oidc_token(pem, iss="https://evil.example.com"))
        is None
    )
    assert backend.verify_token(db, oidc_token(pem, minutes=-1)) is None
    assert backend.verify_token(db, "garbage") is None

    # A server-signed token is not accepted by the oidc backend
    assert backend.verify_token(db, tokens.create_access_token("alice", "oidc")) is None

    assert backend.authenticate(db, "alice", "password") is None
    with pytest.raises(AuthError):
        backend.issue_token(principal)


def test_oidc_backend_username_claim_override(db, use_backend, rsa_keypair):
    pem, public_jwk = rsa_keypair
    use_backend("oidc", oidc_username_claim="email", **OIDC_SETTINGS)
    backend = OidcBackend(jwks_loader=lambda: {"keys": [public_jwk]})
    principal = backend.verify_token(db, oidc_token(pem, email="alice@example.com"))
    assert principal.user_name == "alice@example.com"
    # No fallback to sub when the configured claim is missing
    assert backend.verify_token(db, oidc_token(pem)) is None


def test_oidc_multi_user_requires_claim_and_system_account(
    db, use_backend, rsa_keypair, monkeypatch
):
    pem, public_jwk = rsa_keypair
    with pytest.raises(AuthError, match="FLUX_OIDC_USERNAME_CLAIM"):
        use_backend("oidc", flux_server_mode="multi-user", **OIDC_SETTINGS)

    me = unprivileged_user()
    if me is None:
        pytest.skip("needs an unprivileged system account")
    use_backend(
        "oidc",
        flux_server_mode="multi-user",
        oidc_username_claim="unix",
        **OIDC_SETTINGS,
    )
    backend = OidcBackend(jwks_loader=lambda: {"keys": [public_jwk]})
    assert backend.verify_token(db, oidc_token(pem, unix=me)).user_name == me
    assert backend.verify_token(db, oidc_token(pem, unix="no-such-user-xyz")) is None


def test_oidc_backend_refreshes_keys_once_on_unknown_kid(
    db, use_backend, rsa_keypair, monkeypatch
):
    pem, public_jwk = rsa_keypair
    use_backend("oidc", **OIDC_SETTINGS)
    pem2, rotated = make_rsa_keypair("test-key-2")
    sets = [{"keys": [public_jwk]}, {"keys": [rotated]}]
    loads = []

    def loader():
        loads.append(1)
        return sets[min(len(loads), len(sets)) - 1]

    now = [1000.0]
    monkeypatch.setattr("flux_restful.auth.oidc.time.monotonic", lambda: now[0])

    backend = OidcBackend(jwks_loader=loader)
    assert backend.verify_token(db, oidc_token(pem, kid="test-key-1")) is not None
    assert len(loads) == 1

    # Unknown kid right after the initial load: within the minimum interval,
    # so no refresh, and the token is rejected
    assert backend.verify_token(db, oidc_token(pem2, kid="test-key-2")) is None
    assert len(loads) == 1

    # After the interval the rotated key is fetched and the token verifies
    now[0] += 61
    assert backend.verify_token(db, oidc_token(pem2, kid="test-key-2")) is not None
    assert len(loads) == 2

    # Junk tokens with random key ids cannot trigger more fetches
    for i in range(100):
        assert backend.verify_token(db, oidc_token(pem, kid=f"random-{i}")) is None
    assert len(loads) == 2

    # A bad token with a known kid never refreshes
    now[0] += 61
    assert backend.verify_token(db, oidc_token(pem2, kid="test-key-2", aud="x")) is None
    assert len(loads) == 2


def test_oidc_rejects_plain_http_endpoints():
    with pytest.raises(AuthError):
        OidcBackend._get_json("http://issuer.example.com/jwks")


def test_oidc_concurrent_requests_share_one_refresh(
    db, use_backend, rsa_keypair, monkeypatch
):
    """
    Verification runs in a thread pool, so requests arriving during a slow
    fetch must not each start their own (they used to).
    """
    import threading

    pem, public_jwk = rsa_keypair
    use_backend("oidc", **OIDC_SETTINGS)
    loads = []
    lock = threading.Lock()

    def slow_loader():
        with lock:
            loads.append(1)
        time.sleep(0.2)
        return {"keys": [public_jwk]}

    backend = OidcBackend(jwks_loader=slow_loader)

    def verify_many(make_token, count=30):
        threads = [
            threading.Thread(target=backend.verify_token, args=(db, make_token(i)))
            for i in range(count)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # The initial load is shared too
    verify_many(lambda i: oidc_token(pem))
    assert len(loads) == 1

    # Junk tokens with unknown key ids, all at once, after the interval
    now = [time.monotonic() + JWKS_REFRESH_MIN_SECONDS + 1]
    monkeypatch.setattr("flux_restful.auth.oidc.time.monotonic", lambda: now[0])
    verify_many(lambda i: oidc_token(pem, kid=f"random-{i}"))
    assert len(loads) == 2


def test_privileged_system_accounts_are_refused(
    db, use_backend, rsa_keypair, monkeypatch
):
    pem, public_jwk = rsa_keypair

    # pam: root exists, and PAM would accept it, but it is below FLUX_MIN_UID
    fake = FakePam(accept={("root", "toor")})
    monkeypatch.setattr(settings, "token_signing_key", "signing-key-for-tests")
    backend = PamBackend(authenticator=fake)
    assert backend.authenticate(db, "root", "toor") is None
    monkeypatch.setattr(settings, "min_uid", 0)
    assert backend.authenticate(db, "root", "toor").user_name == "root"

    # oidc in multi-user mode: a claim mapping to root is refused
    monkeypatch.setattr(settings, "min_uid", 1000)
    use_backend(
        "oidc",
        flux_server_mode="multi-user",
        oidc_username_claim="unix",
        **OIDC_SETTINGS,
    )
    backend = OidcBackend(jwks_loader=lambda: {"keys": [public_jwk]})
    assert backend.verify_token(db, oidc_token(pem, unix="root")) is None
    monkeypatch.setattr(settings, "min_uid", 0)
    assert backend.verify_token(db, oidc_token(pem, unix="root")).user_name == "root"
