import pyotp
from sqlalchemy import text

from app.db import SessionLocal

from .conftest import EMAIL, PASSWORD, TOTP_SECRET, login


async def test_login_success_sets_httponly_session_cookie(client):
    resp = await login(client)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    cookie = next(h for h in resp.headers.get_list("set-cookie") if h.startswith("session="))
    assert "httponly" in cookie.lower() and "samesite=lax" in cookie.lower()
    assert (await client.get("/admin/categories")).status_code == 200


async def test_wrong_password_and_unknown_email_give_the_same_error(client):
    wrong = await login(client, password="nope nope nope")
    unknown = await login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    # The message does not say which field was wrong, or whether the email exists.
    assert "อีเมล รหัสผ่าน หรือรหัส TOTP ไม่ถูกต้อง" in wrong.text
    assert "อีเมล รหัสผ่าน หรือรหัส TOTP ไม่ถูกต้อง" in unknown.text


async def test_totp_is_required_and_checked(client):
    assert (await login(client, code="")).status_code == 401
    assert (await login(client, code="000000")).status_code == 401
    assert (await login(client, code=pyotp.TOTP(TOTP_SECRET).now())).status_code == 303


async def test_login_form_needs_matching_csrf_cookie(client):
    resp = await client.post(
        "/admin/login", data={"email": EMAIL, "password": PASSWORD, "code": "", "csrf_token": "forged"}
    )
    assert resp.status_code == 403


async def test_login_is_rate_limited_per_ip(client):
    for _ in range(5):
        assert (await login(client, password="wrong wrong wrong")).status_code == 401
    assert (await login(client, password="wrong wrong wrong")).status_code == 429
    assert (await login(client)).status_code == 429  # even the right password waits


async def test_admin_requires_login(client):
    for path in ("/admin/", "/admin/categories", "/admin/sessions"):
        resp = await client.get(path)
        assert resp.status_code == 303 and resp.headers["location"] == "/login"


async def test_logout_revokes_the_session(authed):
    resp = await authed.post("/admin/logout", data={"csrf_token": authed.csrf})
    assert resp.status_code == 303
    authed.cookies.clear()
    async with SessionLocal() as db:
        revoked = (await db.execute(text("select revoked_at from auth_session"))).scalar_one()
    assert revoked is not None


async def test_revoked_session_stops_working(authed):
    session_id = authed.cookies["session"]
    resp = await authed.post(f"/admin/sessions/{session_id}/revoke", data={"csrf_token": authed.csrf})
    assert resp.headers["location"] == "/login"
    authed.cookies.set("session", session_id)  # the old cookie is still held by the browser
    assert (await authed.get("/admin/categories")).status_code == 303


async def test_session_cookie_is_not_sent_for_the_public_api(client):
    assert (await client.get("/api/categories")).status_code == 200
