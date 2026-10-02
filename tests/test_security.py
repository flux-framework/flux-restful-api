"""
Unit tests for password hashing (no Flux needed).
"""

import pytest

from flux_restful.core import security


def test_hash_and_verify_roundtrip():
    hashed = security.get_password_hash("12345")
    assert hashed.startswith("$2b$")
    assert security.verify_password("12345", hashed) is True
    assert security.verify_password("12346", hashed) is False
    assert security.verify_password("", hashed) is False

    # A new salt every time
    assert security.get_password_hash("12345") != hashed


# Produced by passlib's CryptContext(schemes=["bcrypt"]).hash("12345") with
# passlib 1.7.4 and bcrypt 4.0.1, i.e. what existing databases contain.
LEGACY_PASSLIB_HASH = "$2b$12$ICFNZWWF0mBXA4pH81Ita.WUdGnI9cyIWyAyxjTA7tNy74AjJigR2"


def test_legacy_passlib_hashes_still_verify():
    # Hashes created before the switch from passlib to bcrypt must keep working
    assert security.verify_password("12345", LEGACY_PASSLIB_HASH) is True
    assert security.verify_password("12346", LEGACY_PASSLIB_HASH) is False


def test_malformed_stored_hash_never_matches():
    assert security.verify_password("12345", "not-a-bcrypt-hash") is False
    assert security.verify_password("12345", "") is False


def test_passwords_over_72_bytes_are_rejected():
    too_long = "a" * 73
    with pytest.raises(ValueError):
        security.get_password_hash(too_long)
    hashed = security.get_password_hash("a" * 72)
    assert security.verify_password("a" * 72, hashed) is True
    assert security.verify_password(too_long, hashed) is False

    # Multi-byte characters count as bytes, not characters
    with pytest.raises(ValueError):
        security.get_password_hash("🥞" * 19)
