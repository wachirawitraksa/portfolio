from urllib.parse import parse_qs, urlparse

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.db import SessionLocal
from app.github import get_github
from app.main import app
from app.models import User
from app.security import verify_password

from .conftest import EMAIL, PASSWORD, TOTP_SECRET, login

NEW_PASSWORD = "a brand new passphrase"


class FakeGitHub:
    """Stands in for GitHub: returns the id we set, or None to mimic a failed exchange."""

    def __init__(self):
        self.id: int | None = 4242
        self.calls: list[tuple[str, str]] = []

    async def user_id(self, code, verifier):
        self.calls.append((code, verifier))
        return self.id


@pytest.fixture
def gh(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://admin.test/auth/github/callback")
    fake = FakeGitHub()
    app.dependency_overrides[get_github] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_github, None)


async def second_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://admin.test")


async def link_id(github_id):
    async with SessionLocal() as db:
        user = (await db.execute(select(User))).scalar_one()
        user.github_user_id = github_id
        await db.commit()


async def stored_user():
    async with SessionLocal() as db:
        return (await db.execute(select(User))).scalar_one()


async def revoked_count():
    async with SessionLocal() as db:
        return (await db.execute(text("select count(*) from auth_session where revoked_at is not null"))).scalar_one()


def query_of(response):
    return parse_qs(urlparse(response.headers["location"]).query)


# --- GitHub OAuth ---------------------------------------------------------------------------


async def test_github_is_off_until_configured(client):
    assert (await client.get("/admin/login/github")).status_code == 404
    assert (await client.get("/admin/auth/github/callback?code=x&state=y")).status_code == 404
    assert "เข้าสู่ระบบด้วย GitHub" not in (await client.get("/admin/login")).text


async def test_github_button_and_redirect_use_state_and_pkce(client, gh):
    assert "เข้าสู่ระบบด้วย GitHub" in (await client.get("/admin/login")).text
    resp = await client.get("/admin/login/github")
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("https://github.com/login/oauth/authorize?")
    q = query_of(resp)
    assert q["client_id"] == ["client-id"] and q["redirect_uri"] == ["http://admin.test/auth/github/callback"]
    assert q["code_challenge_method"] == ["S256"] and q["code_challenge"] and q["state"] and q["allow_signup"] == ["false"]
    cookie = next(h for h in resp.headers.get_list("set-cookie") if h.startswith("oauth_state="))
    assert "httponly" in cookie.lower() and "samesite=lax" in cookie.lower()


async def test_login_with_a_linked_github_account(client, gh):
    await link_id(4242)
    start = await client.get("/admin/login/github")
    resp = await client.get(f"/admin/auth/github/callback?code=abc&state={query_of(start)['state'][0]}")
    assert resp.status_code == 303 and resp.headers["location"] == "/"
    assert (await client.get("/admin/categories")).status_code == 200
    code, verifier = gh.calls[0]
    assert code == "abc" and verifier  # the PKCE verifier from the cookie goes to the exchange


async def test_unknown_github_account_cannot_log_in_and_creates_nothing(client, gh):
    await link_id(999)  # someone else's id is the one on file
    start = await client.get("/admin/login/github")
    resp = await client.get(f"/admin/auth/github/callback?code=abc&state={query_of(start)['state'][0]}")
    assert resp.status_code == 403 and "เข้าสู่ระบบด้วย GitHub ไม่สำเร็จ" in resp.text
    assert (await client.get("/admin/categories")).status_code == 303
    async with SessionLocal() as db:
        assert len((await db.execute(select(User))).scalars().all()) == 1


async def test_callback_rejects_wrong_missing_or_replayed_state(client, gh):
    await link_id(4242)
    assert (await client.get("/admin/auth/github/callback?code=abc&state=x")).status_code == 403  # no cookie
    start = await client.get("/admin/login/github")
    state = query_of(start)["state"][0]
    assert (await client.get("/admin/auth/github/callback?code=abc&state=forged")).status_code == 403
    assert not gh.calls  # a bad state never reaches GitHub
    # The failed attempt cleared the cookie, so even the right state cannot be used afterwards.
    assert (await client.get(f"/admin/auth/github/callback?code=abc&state={state}")).status_code == 403
    assert (await client.get("/admin/categories")).status_code == 303


async def test_failed_github_exchange_logs_nobody_in(client, gh):
    await link_id(4242)
    gh.id = None
    start = await client.get("/admin/login/github")
    resp = await client.get(f"/admin/auth/github/callback?code=bad&state={query_of(start)['state'][0]}")
    assert resp.status_code == 403
    assert (await client.get("/admin/categories")).status_code == 303


async def test_link_github_from_the_account_page(authed, gh):
    assert "เชื่อมบัญชี GitHub" in (await authed.get("/admin/account")).text
    start = await authed.post("/admin/account/github/link", data={"csrf_token": authed.csrf})
    assert start.status_code == 303
    resp = await authed.get(f"/admin/auth/github/callback?code=abc&state={query_of(start)['state'][0]}")
    assert resp.headers["location"] == "/account?notice=github_linked"
    assert (await stored_user()).github_user_id == 4242
    assert "ยกเลิกการเชื่อม" in (await authed.get("/admin/account")).text


async def test_link_needs_a_login_and_csrf(authed, gh):
    assert (await authed.post("/admin/account/github/link", data={})).status_code == 403
    visitor = await second_client()  # not logged in
    start = await visitor.get("/admin/login/github")
    resp = await visitor.get(f"/admin/auth/github/callback?code=abc&state={query_of(start)['state'][0]}")
    assert resp.status_code == 403  # login mode: nobody linked yet
    await visitor.aclose()
    start = await authed.post("/admin/account/github/link", data={"csrf_token": authed.csrf})
    authed.cookies.delete("session")
    resp = await authed.get(f"/admin/auth/github/callback?code=abc&state={query_of(start)['state'][0]}")
    assert resp.headers["location"] == "/login"
    assert (await stored_user()).github_user_id is None


async def test_unlink_github(authed, gh):
    await link_id(4242)
    resp = await authed.post("/admin/account/github/unlink", data={"csrf_token": authed.csrf})
    assert resp.headers["location"] == "/account?notice=github_unlinked"
    assert (await stored_user()).github_user_id is None


# --- password and TOTP changes end every session --------------------------------------------


async def test_change_password_ends_all_sessions(authed):
    other = await second_client()
    assert (await login(other)).status_code == 303  # a second device
    resp = await authed.post(
        "/admin/account/password",
        data={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
            "csrf_token": authed.csrf,
        },
    )
    assert resp.status_code == 303 and resp.headers["location"] == "/login"
    assert await revoked_count() == 2
    assert (await other.get("/admin/categories")).status_code == 303  # the other device is out too
    assert verify_password((await stored_user()).password_hash, NEW_PASSWORD)
    assert (await login(other, password=PASSWORD)).status_code == 401  # the old one no longer works
    assert (await login(other, password=NEW_PASSWORD)).status_code == 303
    await other.aclose()


@pytest.mark.parametrize(
    ("data", "status", "message"),
    [
        ({"current_password": "wrong wrong wrong", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD}, 403, "รหัสผ่านปัจจุบันไม่ถูกต้อง"),
        ({"current_password": PASSWORD, "new_password": "short", "confirm_password": "short"}, 422, "อย่างน้อย 12"),
        ({"current_password": PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": "different"}, 422, "ไม่ตรงกัน"),
    ],
)
async def test_change_password_refusals_change_nothing(authed, data, status, message):
    resp = await authed.post("/admin/account/password", data={**data, "csrf_token": authed.csrf})
    assert resp.status_code == status and message in resp.text
    assert verify_password((await stored_user()).password_hash, PASSWORD)
    assert await revoked_count() == 0
    assert (await authed.get("/admin/categories")).status_code == 200


async def test_password_guessing_on_the_account_page_is_rate_limited(authed):
    bad = {"current_password": "wrong wrong wrong", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD}
    for _ in range(5):
        assert (await authed.post("/admin/account/password", data={**bad, "csrf_token": authed.csrf})).status_code == 403
    assert (await authed.post("/admin/account/password", data={**bad, "csrf_token": authed.csrf})).status_code == 429
    good = {**bad, "current_password": PASSWORD, "csrf_token": authed.csrf}
    assert (await authed.post("/admin/account/password", data=good)).status_code == 429  # even the right one waits


async def test_reset_totp_shows_the_new_secret_once_and_ends_all_sessions(authed):
    resp = await authed.post(
        "/admin/account/totp/reset", data={"current_password": PASSWORD, "csrf_token": authed.csrf}
    )
    assert resp.status_code == 200 and resp.headers["cache-control"] == "no-store"
    secret = (await stored_user()).totp_secret
    assert secret != TOTP_SECRET and secret in resp.text
    assert await revoked_count() == 1
    assert (await authed.get("/admin/categories")).status_code == 303
    fresh = await second_client()
    assert (await login(fresh, code=pyotp.TOTP(TOTP_SECRET).now())).status_code == 401  # old secret is dead
    assert (await login(fresh, code=pyotp.TOTP(secret).now())).status_code == 303
    await fresh.aclose()


async def test_reset_totp_needs_the_current_password(authed):
    resp = await authed.post(
        "/admin/account/totp/reset", data={"current_password": "wrong wrong wrong", "csrf_token": authed.csrf}
    )
    assert resp.status_code == 403
    assert (await stored_user()).totp_secret == TOTP_SECRET and await revoked_count() == 0


async def test_account_pages_need_login_and_csrf(authed):
    assert (await authed.post("/admin/account/password", data={"current_password": PASSWORD})).status_code == 403
    assert (await authed.post("/admin/account/totp/reset", data={"current_password": PASSWORD})).status_code == 403
    assert (await authed.post("/admin/account/github/unlink", data={})).status_code == 403
    assert EMAIL in (await authed.get("/admin/account")).text
    visitor = await second_client()  # `client` and `authed` are the same logged-in object, so use a new one
    assert (await visitor.get("/admin/account")).status_code == 303
    assert (await visitor.post("/admin/account/password", data={})).status_code == 303
    assert (await visitor.post("/admin/account/github/link", data={})).status_code == 303
    await visitor.aclose()
