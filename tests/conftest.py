import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(here)
if root not in sys.path:
    sys.path.insert(0, root)

import app.auth as auth  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.crud import user as crud_user  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.schemas.user import UserCreate  # noqa: E402


@pytest.fixture
def db():
    """
    A database session with tables created.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_user(db):
    """
    Create (or replace) a database user.
    """

    def _make(username="testuser", password="testpass", superuser=False, active=True):
        existing = crud_user.get_by_username(db, user_name=username)
        if existing:
            db.delete(existing)
            db.commit()
        return crud_user.create(
            db,
            obj_in=UserCreate(
                user_name=username,
                password=password,
                is_superuser=superuser,
                is_active=active,
            ),
        )

    return _make


@pytest.fixture
def use_backend(monkeypatch):
    """
    Switch the auth backend (and any other settings) for one test.
    """

    def _use(name, **overrides):
        monkeypatch.setattr(settings, "auth_backend", name)
        monkeypatch.setattr(settings, "require_auth", name != "none")
        if not settings.token_signing_key:
            monkeypatch.setattr(settings, "token_signing_key", "signing-key-for-tests")
        for key, value in overrides.items():
            monkeypatch.setattr(settings, key, value)
        auth.reset_backend()
        return auth.get_backend()

    yield _use
    auth.reset_backend()


@pytest.fixture(scope="session")
def live_server():
    """
    The app served by uvicorn in a background thread, for tests that need
    real HTTP behavior (the test client runs each request to completion
    before returning, so streaming responses cannot be observed through it).
    Yields the base URL.
    """
    import socket
    import threading
    import time

    import httpx
    import uvicorn

    from app.main import app

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            httpx.get(base + "/v1/auth", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    yield base
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def client():
    """
    A test client for the application (requires a running Flux instance).
    """
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def make_rsa_keypair(kid="test-key-1"):
    """
    A private key PEM and matching public JWK, for signing OIDC-style tokens.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jose import jwk

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")
    public = jwk.construct(pem, "RS256").public_key().to_dict()
    public.update({"kid": kid, "use": "sig"})
    return pem, public


@pytest.fixture(scope="session")
def rsa_keypair():
    return make_rsa_keypair()


def oidc_token(pem, kid="test-key-1", minutes=5, **claims):
    """
    Sign an OIDC-style id token with a private key PEM.
    """
    from jose import jwt

    now = datetime.now(timezone.utc)
    payload = {
        "iss": "https://issuer.example.com",
        "aud": "flux-restful",
        "sub": "alice",
        "preferred_username": "Alice Display Name",
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    payload.update(claims)
    return jwt.encode(payload, pem, algorithm="RS256", headers={"kid": kid})


def unprivileged_user():
    """
    A system account at or above FLUX_MIN_UID to use as a login: the account
    running the tests if it qualifies, otherwise another one (CI runs as root).
    Returns None if there is none.
    """
    import pwd

    me = pwd.getpwuid(os.getuid())
    if me.pw_uid >= settings.min_uid:
        return me.pw_name
    for record in pwd.getpwall():
        if settings.min_uid <= record.pw_uid < 65000:
            return record.pw_name
    return None
