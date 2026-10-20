import pyotp
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .. import github
from ..config import get_settings
from ..db import get_db
from ..deps import COOKIE, current_session, current_user, require_csrf
from ..models import AuthSession, User
from ..ratelimit import password_limiter
from ..security import hash_password, verify_password
from ..sessions import revoke_all_sessions
from ..templating import templates
from .auth import client_ip, go

router = APIRouter(prefix="/account")

MIN_PASSWORD = 12
NOTICES = {
    "github_linked": "เชื่อมบัญชี GitHub แล้ว",
    "github_failed": "เชื่อมบัญชี GitHub ไม่สำเร็จ (ยืนยันกับ GitHub ไม่ผ่าน หรือบัญชีนี้ถูกใช้อยู่)",
    "github_unlinked": "ยกเลิกการเชื่อม GitHub แล้ว",
}


def account_page(request: Request, session: AuthSession, user: User, error=None, notice=None, status=200):
    context = {
        "user": user,
        "github_enabled": github.enabled(),
        "github_linked": user.github_user_id is not None,
        "has_totp": bool(user.totp_secret),
        "min_password": MIN_PASSWORD,
        "error": error,
        "notice": NOTICES.get(notice or ""),
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "account.html", context, status_code=status)


def password_is_right(request: Request, user: User, password: str) -> bool | None:
    """True/False for the check, None when this IP has tried too often."""
    limit = get_settings().login_attempts_per_minute
    if not password_limiter.allow(client_ip(request), limit):
        return None
    return verify_password(user.password_hash, password)


@router.get("", response_class=HTMLResponse)
async def show(
    request: Request,
    notice: str = "",
    session: AuthSession = Depends(current_session),
    user: User = Depends(current_user),
):
    return account_page(request, session, user, notice=notice)


@router.post("/password")
async def change_password(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    session: AuthSession = Depends(current_session),
    user: User = Depends(current_user),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    ok = password_is_right(request, user, current_password)
    if ok is None:
        return account_page(request, session, user, "ลองบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่", status=429)
    if not ok:
        return account_page(request, session, user, "รหัสผ่านปัจจุบันไม่ถูกต้อง", status=403)
    if len(new_password) < MIN_PASSWORD:
        return account_page(request, session, user, f"รหัสผ่านใหม่ต้องยาวอย่างน้อย {MIN_PASSWORD} ตัวอักษร", status=422)
    if new_password != confirm_password:
        return account_page(request, session, user, "รหัสผ่านใหม่สองช่องไม่ตรงกัน", status=422)
    user.password_hash = hash_password(new_password)
    await revoke_all_sessions(db, user.id)  # every login ends, this one included
    await db.commit()
    resp = go("/login")
    resp.delete_cookie(COOKIE)
    return resp


@router.post("/totp/reset")
async def reset_totp(
    request: Request,
    current_password: str = Form(""),
    session: AuthSession = Depends(current_session),
    user: User = Depends(current_user),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    ok = password_is_right(request, user, current_password)
    if ok is None:
        return account_page(request, session, user, "ลองบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่", status=429)
    if not ok:
        return account_page(request, session, user, "รหัสผ่านปัจจุบันไม่ถูกต้อง", status=403)
    secret = pyotp.random_base32()
    user.totp_secret = secret
    await revoke_all_sessions(db, user.id)
    await db.commit()
    # Shown once, on this response only. The login that showed it is already over.
    resp = templates.TemplateResponse(
        request,
        "totp_reset.html",
        {
            "secret": secret,
            "uri": pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Portfolio admin"),
            "hide_nav": True,
        },
    )
    resp.headers["Cache-Control"] = "no-store"
    resp.delete_cookie(COOKIE)
    return resp


@router.post("/github/link")
async def link_github(_: None = Depends(require_csrf)):
    if not github.enabled():
        raise HTTPException(404)
    return github.start("link")


@router.post("/github/unlink")
async def unlink_github(
    user: User = Depends(current_user), _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    user.github_user_id = None
    await db.commit()
    return go("/account?notice=github_unlinked")
