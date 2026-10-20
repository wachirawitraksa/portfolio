import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import github
from ..config import get_settings
from ..db import get_db
from ..deps import COOKIE, LoginRequired, current_session, require_csrf
from ..github import GitHub, get_github
from ..models import AuthSession, User
from ..netutil import client_ip
from ..ratelimit import login_limiter
from ..security import expiry, new_token, verify_password, verify_totp
from ..templating import templates

router = APIRouter()

LOGIN_CSRF = "login_csrf"
# Same message for every failure, so it never says which field was wrong.
GENERIC_ERROR = "อีเมล รหัสผ่าน หรือรหัส TOTP ไม่ถูกต้อง"
GITHUB_ERROR = "เข้าสู่ระบบด้วย GitHub ไม่สำเร็จ"


def go(path: str) -> RedirectResponse:
    # Paths are what the browser sees on the admin host, which has no /admin prefix.
    return RedirectResponse(path, status_code=303)


def login_page(request: Request, error: str | None = None, status: int = 200):
    """The login form, with a fresh CSRF token in the form and in a cookie."""
    token = new_token()
    resp = templates.TemplateResponse(
        request, "login.html", {"csrf": token, "error": error, "github": github.enabled()}, status_code=status
    )
    resp.set_cookie(LOGIN_CSRF, token, httponly=True, samesite="lax", secure=get_settings().cookie_secure)
    return resp


async def open_session(request: Request, db: AsyncSession, user: User) -> RedirectResponse:
    """Start a login for this user and send them to the admin home."""
    settings = get_settings()
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


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return login_page(request)


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
    if not login_limiter.allow(client_ip(request), settings.login_attempts_per_minute):
        return login_page(request, "ลองบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่", 429)
    if not csrf_token or csrf_token != request.cookies.get(LOGIN_CSRF):
        return login_page(request, GENERIC_ERROR, 403)

    user = (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
    password_ok = verify_password(user.password_hash if user else None, password)
    totp_ok = verify_totp(user.totp_secret if user else None, code) if user else False
    if not (user and password_ok and totp_ok):
        return login_page(request, GENERIC_ERROR, 401)
    return await open_session(request, db, user)


@router.get("/login/github")
async def login_with_github():
    if not github.enabled():
        raise HTTPException(404)
    return github.start("login")


@router.get("/auth/github/callback")
async def github_callback(
    request: Request,
    code: str = "",
    state: str = "",
    db: AsyncSession = Depends(get_db),
    gh: GitHub = Depends(get_github),
):
    """Both "log in with GitHub" and "link my GitHub" come back here; the cookie says which."""
    if not github.enabled():
        raise HTTPException(404)
    if not login_limiter.allow(client_ip(request), get_settings().login_attempts_per_minute):
        return login_page(request, "ลองบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่", 429)

    mode, expected_state, verifier = github.read_cookie(request.cookies.get(github.OAUTH_COOKIE, ""))
    if not (mode and code and state and secrets.compare_digest(expected_state, state)):
        resp = login_page(request, GITHUB_ERROR, 403)
        resp.delete_cookie(github.OAUTH_COOKIE)
        return resp
    github_id = await gh.user_id(code, verifier)

    if mode == "link":
        try:
            session = await current_session(request, db)
        except LoginRequired:
            return go("/login")
        user = await db.get(User, session.user_id)
        taken = (
            await db.execute(select(User).where(User.github_user_id == github_id, User.id != user.id))
        ).scalar_one_or_none()
        if github_id is None or taken is not None:
            resp = go("/account?notice=github_failed")
        else:
            user.github_user_id = github_id
            await db.commit()
            resp = go("/account?notice=github_linked")
        resp.delete_cookie(github.OAUTH_COOKIE)
        return resp

    # Log in: only a user whose GitHub id was linked beforehand. Nothing is ever created here.
    user = (
        (await db.execute(select(User).where(User.github_user_id == github_id))).scalar_one_or_none()
        if github_id is not None
        else None
    )
    if user is None:
        resp = login_page(request, GITHUB_ERROR, 403)
        resp.delete_cookie(github.OAUTH_COOKIE)
        return resp
    resp = await open_session(request, db, user)
    resp.delete_cookie(github.OAUTH_COOKIE)
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
