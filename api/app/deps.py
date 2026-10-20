from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import AuthSession, User

COOKIE = "session"


class LoginRequired(Exception):
    pass


async def current_session(request: Request, db: AsyncSession = Depends(get_db)) -> AuthSession:
    sid = request.cookies.get(COOKIE)
    row = await db.get(AuthSession, sid) if sid else None
    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        raise LoginRequired()
    user = await db.get(User, row.user_id)
    request.state.admin_email = user.email if user else ""  # drawn in the admin menu
    return row


async def current_user(
    session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)
) -> User:
    user = await db.get(User, session.user_id)
    if user is None:
        raise LoginRequired()
    return user


async def require_csrf(request: Request, session: AuthSession = Depends(current_session)) -> None:
    """Every mutation under /admin goes through this."""
    form = await request.form()
    if form.get("csrf_token") != session.csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token mismatch")
