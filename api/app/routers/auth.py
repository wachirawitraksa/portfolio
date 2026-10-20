from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_db
from ..deps import COOKIE, current_session, require_csrf
from ..models import AuthSession, User
from ..ratelimit import login_limiter
from ..security import expiry, new_token, verify_password, verify_totp
from ..templating import templates

router = APIRouter()

LOGIN_CSRF = "login_csrf"
# Same message for every failure, so it never says which field was wrong.
GENERIC_ERROR = "อีเมล รหัสผ่าน หรือรหัส TOTP ไม่ถูกต้อง"


def go(path: str) -> RedirectResponse:
    # Paths are what the browser sees on the admin host, which has no /admin prefix.
    return RedirectResponse(path, status_code=303)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    token = new_token()
    resp = templates.TemplateResponse(request, "login.html", {"csrf": token, "error": None})
    resp.set_cookie(
        LOGIN_CSRF, token, httponly=True, samesite="lax", secure=get_settings().cookie_secure
    )
    return resp


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    code: str = Form(""),
    csrf_token: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    def fail(message: str, status: int = 401):
        token = new_token()
        resp = templates.TemplateResponse(
            request, "login.html", {"csrf": token, "error": message}, status_code=status
        )
        resp.set_cookie(LOGIN_CSRF, token, httponly=True, samesite="lax", secure=settings.cookie_secure)
        return resp

    if not login_limiter.allow(client_ip(request), settings.login_attempts_per_minute):
        return fail("ลองบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่", 429)
    if not csrf_token or csrf_token != request.cookies.get(LOGIN_CSRF):
        return fail(GENERIC_ERROR, 403)

    user = (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
    password_ok = verify_password(user.password_hash if user else None, password)
    totp_ok = verify_totp(user.totp_secret if user else None, code) if user else False
    if not (user and password_ok and totp_ok):
        return fail(GENERIC_ERROR)

    session = AuthSession(
        id=new_token(),
        user_id=user.id,
        csrf_token=new_token(),
        expires_at=expiry(settings.session_days),
        ip=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:255],
    )
    db.add(session)
    await db.commit()

    resp = go("/")
    resp.set_cookie(
        COOKIE,
        session.id,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_days * 86400,
    )
    resp.delete_cookie(LOGIN_CSRF)
    return resp


@router.post("/logout")
async def logout(
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    session.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    resp = go("/login")
    resp.delete_cookie(COOKIE)
    return resp


@router.get("/sessions", response_class=HTMLResponse)
async def sessions_page(
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(AuthSession)
            .where(
                AuthSession.user_id == session.user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.created_at.desc())
        )
    ).scalars().all()
    return templates.TemplateResponse(
        request, "sessions.html", {"rows": rows, "current": session, "csrf": session.csrf_token}
    )


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(AuthSession, session_id)
    # Only this user's own sessions can be revoked.
    if target and target.user_id == session.user_id and target.revoked_at is None:
        target.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    resp = go("/login" if session_id == session.id else "/sessions")
    if session_id == session.id:
        resp.delete_cookie(COOKIE)
    return resp
