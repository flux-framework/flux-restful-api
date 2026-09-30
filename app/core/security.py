import bcrypt

# bcrypt silently ignored bytes past 72 in older versions and raises in >= 5.0.
# We reject longer passwords explicitly so behavior is the same everywhere.
MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password cannot be longer than {MAX_PASSWORD_BYTES} bytes.")
    return encoded


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Over-long password or malformed stored hash: never a match
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password with bcrypt (a random salt is generated per hash).
    """
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")
