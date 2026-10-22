"""Links that show a draft on the real website for a few minutes.

The admin makes one when "preview on the site" is clicked. It names one project or article and expires quickly.
It is signed with a key derived from the admin's password hash, so changing the password also ends every
preview link, and nothing new has to be configured."""
import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .models import User

LIFETIME = 600  # seconds


async def _key(db: AsyncSession) -> bytes:
    secret = (await db.execute(select(User.password_hash).order_by(User.id).limit(1))).scalar_one_or_none()
    if not secret:
        raise HTTPException(404)
    return hashlib.sha256(f"preview:{secret}".encode()).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


async def mint(db: AsyncSession, kind: str, item_id: int, now: float | None = None) -> str:
    body = _b64(json.dumps({"k": kind, "i": item_id, "e": int((now or time.time()) + LIFETIME)}).encode())
    return f"{body}.{_b64(hmac.new(await _key(db), body.encode(), hashlib.sha256).digest())}"


async def valid(db: AsyncSession, token: str | None, kind: str, item_id: int, now: float | None = None) -> bool:
    if not token or token.count(".") != 1:
        return False
    body, signature = token.split(".")
    expected = _b64(hmac.new(await _key(db), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except ValueError:
        return False
    return data.get("k") == kind and data.get("i") == item_id and data.get("e", 0) >= (now or time.time())


def site_base(request: Request) -> str:
    """Where the public website lives: SITE_URL when set, otherwise this admin host without its "admin." prefix
    (admin.example.com -> example.com, admin.localhost:8080 -> localhost:8080)."""
    if configured := get_settings().site_url.strip().rstrip("/"):
        return configured
    host = request.headers.get("host", "")
    host = host.removeprefix("admin.")
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{scheme}://{host}"
