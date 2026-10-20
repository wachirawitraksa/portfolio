import secrets
from datetime import datetime, timedelta, timezone

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()  # argon2id by default

# Verified against when the email is unknown, so timing does not reveal it.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except VerifyMismatchError:
        return False


def verify_totp(secret: str | None, code: str) -> bool:
    if not secret:
        return True
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def expiry(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)
