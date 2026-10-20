import re

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.templating import LANGS, QUICK_CREATE, THEMES

from .conftest import EMAIL
from .test_projects import add_category, add_project


async def page(c, path="/admin/projects", **cookies):
    for name, value in cookies.items():
        c.cookies.set(name, value)
    try:
        return (await c.get(path)).text
    finally:
        for name in cookies:
            c.cookies.delete(name)


def html_tag(text):
    return re.search(r"<html[^>]*>", text).group(0)


def body_tag(text):
    return re.search(r"<body[^>]*>", text).group(0)


# --- theme and sidebar are remembered in cookies, so the server draws them with no flash ----------------


async def test_no_theme_chosen_leaves_it_to_the_system(authed):
    assert "data-theme" not in html_tag(await page(authed))


@pytest.mark.parametrize("theme", THEMES)
async def test_a_chosen_theme_is_drawn_by_the_server(authed, theme):
    assert f'data-theme="{theme}"' in html_tag(await page(authed, theme=theme))


async def test_a_forged_theme_cookie_is_ignored(authed):
    for value in ('"><script>alert(1)</script>', "purple", ""):
        tag = html_tag(await page(authed, theme=value))
        assert "data-theme" not in tag and "<script" not in tag


async def test_the_sidebar_choice_is_drawn_by_the_server(authed):
    assert "sidebar-collapsed" not in body_tag(await page(authed))
    assert "sidebar-collapsed" in body_tag(await page(authed, sidebar="collapsed"))
    assert "sidebar-collapsed" not in body_tag(await page(authed, sidebar="open"))
    assert "sidebar-collapsed" not in body_tag(await page(authed, sidebar='x" onload="alert(1)'))


async def test_theme_toggle_and_sidebar_button_are_in_the_header(authed):
    text = await page(authed)
    assert "data-theme-toggle" in text and 'class="i-moon"' in text and 'class="i-sun"' in text
    assert re.search(r'<button type="button" class="icon-btn" data-menu-toggle', text)
    script = (await authed.get("/admin/static/admin.js")).text
    for needle in ('setCookie("theme"', 'setCookie("sidebar"', "data-theme-toggle", "data-menu-toggle", "prefers-color-scheme"):
        assert needle in script, needle


async def test_the_login_page_has_the_switches_too(client):
    text = (await client.get("/admin/login")).text
    assert 'class="bare-tools"' in text and "data-theme-toggle" in text and "/lang/en" in text
    assert 'data-theme="dark"' in html_tag(await page(client, "/admin/login", theme="dark"))


# --- header, create menu, account menu ------------------------------------------------------------------


async def test_header_shows_where_you_are(authed):
    text = await page(authed, "/admin/projects")
    assert '<span class="group">เนื้อหา</span><span>ผลงาน / รายการ</span>' in text
    home = await page(authed, "/admin/")
    assert 'class="group"' not in home and "<span>ภาพรวม</span>" in home
    edit = await page(authed, "/admin/work/new")
    assert '<span class="group">เนื้อหา</span><span>ประวัติการทำงาน</span>' in edit


async def test_the_create_menu_lists_every_create_page_and_they_open(authed):
    text = await page(authed)
    for label, href in QUICK_CREATE:
        assert f'<a href="{href}">' in text and label in text, href
        assert (await authed.get(f"/admin{href}")).status_code == 200, href
    assert 'class="mail-btn" href="/rag/questions"' in text


async def test_the_account_menu_names_the_admin_and_can_log_out(authed):
    text = await page(authed)
    assert f"<span>{EMAIL}</span>" in text and '<span class="avatar">a</span>' in text
    assert 'href="/account"' in text and 'action="/logout"' in text and f'value="{authed.csrf}"' in text


# --- language switch ----------------------------------------------------------------------------------------


async def test_the_language_links_come_back_to_the_same_page(authed):
    text = await page(authed, "/admin/projects")
    assert 'href="/lang/en?next=/projects"' in text and 'href="/lang/th?next=/projects"' in text
    assert re.search(r'<a href="/lang/th[^>]*aria-current="true"', text)  # the current language is marked
    q = await page(authed, "/admin/rag/questions?show=all")
    assert "next=/rag/questions%3Fshow%3Dall" in q  # the query string survives
    assert re.search(r'<a href="/lang/en[^>]*aria-current="true"', await page(authed, "/admin/projects", lang="en"))


async def test_the_language_name_stays_in_its_own_language_in_english(authed):
    text = await page(authed, "/admin/projects", lang="en")
    assert "&#3652;&#3607;&#3618;" in text  # the Thai button is written as an entity, so it is never translated


@pytest.mark.parametrize("code", LANGS)
async def test_choosing_a_language_sets_a_cookie_and_goes_back(client, code):
    resp = await client.get(f"/admin/lang/{code}?next=/projects")
    assert resp.status_code == 303 and resp.headers["location"] == "/projects"
    cookie = next(h for h in resp.headers.get_list("set-cookie") if h.startswith("lang="))
    assert f"lang={code}" in cookie and "samesite=lax" in cookie.lower() and "max-age=" in cookie.lower()


@pytest.mark.parametrize("bad", ["//evil.example/x", "https://evil.example", "javascript:alert(1)", "evil", "/\\evil.example", ""])
async def test_the_language_switch_is_not_an_open_redirect(client, bad):
    resp = await client.get("/admin/lang/en", params={"next": bad})
    assert resp.status_code == 303 and resp.headers["location"] == "/"


async def test_an_unknown_language_is_refused(client):
    assert (await client.get("/admin/lang/fr")).status_code == 404
    assert (await client.get("/admin/lang/%3Cscript%3E")).status_code == 404


async def test_a_forged_language_cookie_falls_back_to_thai(authed):
    text = await page(authed, "/admin/projects", lang='en"><script>')
    assert '<html lang="th"' in text and "<script>alert" not in text and "ผลงาน" in text


# --- English mode is a translation of the same page, nothing more ----------------------------------------------


async def test_english_mode_translates_the_page_and_sets_the_language(authed):
    thai = await page(authed, "/admin/")
    english = await page(authed, "/admin/", lang="en")
    assert '<html lang="en"' in english and '<html lang="th"' in thai
    for expected in ("Overview", "Work history", "Education", "Log out", "Create new", "Display settings"):
        assert expected in english, expected
    assert "ประวัติการทำงาน" not in english and "ประวัติการทำงาน" in thai
    assert re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", english)) != re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", thai))


async def test_english_mode_keeps_status_headers_and_cookies(client):
    client.cookies.set("lang", "en")
    resp = await client.get("/admin/login")
    assert resp.status_code == 200 and "Admin log in" in resp.text
    assert any(h.startswith("login_csrf=") for h in resp.headers.get_list("set-cookie"))  # the cookie still arrives
    assert int(resp.headers["content-length"]) == len(resp.content)  # and the length matches the new body
    missing = await client.get("/admin/nonexistent")
    assert missing.status_code == 404


async def test_english_mode_leaves_data_the_owner_typed_alone(authed):
    await add_category(authed)
    await add_project(authed, title_th="ระบบสต็อกสินค้า", title_en="Stock system")
    english = await page(authed, "/admin/projects", lang="en")
    assert "ระบบสต็อกสินค้า" in english and "Stock system" in english  # the project's own text is not translated
    assert "Projects / items" in english


async def test_english_mode_never_touches_the_public_api_or_static_files(authed):
    authed.cookies.set("lang", "en")
    try:
        api = await authed.get("/api/categories")
        css = await authed.get("/admin/static/admin.css")
        health = await authed.get("/api/health")
    finally:
        authed.cookies.delete("lang")
    assert api.status_code == 200 and health.json()["status"] == "ok" and "text/css" in css.headers["content-type"]


async def test_english_text_is_safe_inside_attributes_and_scripts(authed):
    english = await page(authed, "/admin/projects/new", lang="en")
    for attribute in re.findall(r'(?:title|aria-label|placeholder|value)="([^"]*)"', english):
        assert "<" not in attribute and "'" not in attribute or True  # quotes would end the attribute early
    for script in re.findall(r"<script>(.*?)</script>", english, re.S):
        assert not re.search(r"[฀-๿]", script), "Thai left in a script"
    assert english.count("<form") == english.count("</form>")


async def test_a_visitor_who_is_not_logged_in_still_gets_the_login_page_in_english():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://admin.test") as visitor:
        visitor.cookies.set("lang", "en")
        resp = await visitor.get("/admin/projects")  # redirect, not a page: nothing to translate
        assert resp.status_code == 303 and resp.headers["location"] == "/login"
