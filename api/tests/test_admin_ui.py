import re

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.templating import NAV, nav_active

from .test_articles import add_article
from .test_projects import add_category, add_project, add_tag
from .test_work import add_work


class Broken:
    async def ping(self):
        raise RuntimeError("down")


async def post(c, path, **data):
    return await c.post(path, data={"csrf_token": c.csrf, **data})


async def home(c):
    resp = await c.get("/admin/")
    assert resp.status_code == 200
    return resp.text


# --- the menu ----------------------------------------------------------------------------------


def test_nav_active_rules():
    assert nav_active("/", "/", True) and not nav_active("/projects", "/", False)
    assert nav_active("/projects", "/projects", False) and nav_active("/projects/3/edit", "/projects", False)
    assert not nav_active("/projects-old", "/projects", False)  # a longer name is a different page
    assert nav_active("/rag", "/rag", True) and not nav_active("/rag/questions", "/rag", True)
    assert nav_active("/rag/questions", "/rag/questions", False)


async def test_every_menu_item_opens_a_real_admin_page(authed):
    for _group, items in NAV:
        for label, href, _exact, _icon in items:
            resp = await authed.get(f"/admin{href}")
            assert resp.status_code == 200, (label, href, resp.status_code)


async def test_menu_is_grouped_marks_the_current_page_and_has_a_logout_form(authed):
    page = await home(authed)
    for group in ("เนื้อหา", "จัดหมวด", "ช่องถามตอบ", "ระบบ"):
        assert re.search(rf'<div class="nav-title[^"]*">{group}</div>', page)
    assert page.count('aria-current="page"') == 1 and re.search(r'<a href="/"[^>]*aria-current="page"', page)
    assert f'<input type="hidden" name="csrf_token" value="{authed.csrf}">' in page and 'action="/logout"' in page
    projects = (await authed.get("/admin/projects/new")).text
    assert re.search(r'<a href="/projects"[^>]*aria-current="page"', projects) and page != projects
    questions = (await authed.get("/admin/rag/questions")).text
    assert re.search(r'<a href="/rag/questions"[^>]*aria-current="page"', questions)
    assert not re.search(r'<a href="/rag"[^>]*aria-current', questions)


async def test_every_admin_page_has_the_menu(authed):
    await add_category(authed)
    await add_project(authed)
    for path in ("/", "/projects", "/projects/1/edit", "/work", "/articles", "/profile", "/settings", "/rag", "/glossary",
                 "/trash", "/account", "/sessions", "/categories", "/kinds", "/tags", "/rag/questions"):
        page = (await authed.get(f"/admin{path}")).text
        assert re.search(r'<aside class="sidebar[ "]', page) and "/static/admin.css" in page, path


async def test_login_page_is_bare_and_asks_nothing_of_the_menu(client):
    page = (await client.get("/admin/login")).text
    assert re.search(r'<body[^>]*class="[^"]*(?<![a-z-])bare', page) and "<aside" not in page and "เข้าสู่ระบบหลังบ้าน" in page


async def test_the_one_time_totp_page_has_no_menu(authed):
    from .conftest import PASSWORD

    page = (await post(authed, "/admin/account/totp/reset", current_password=PASSWORD)).text
    assert "<aside" not in page and "รหัสลับ" in page


# --- assets: nothing from another site ------------------------------------------------------------


async def test_assets_are_served_from_the_api_itself(client):
    for path, kind in (("css", "text/css"), ("js", "javascript")):
        resp = await client.get(f"/admin/static/admin.{path}")
        assert resp.status_code == 200 and kind in resp.headers["content-type"] and len(resp.content) > 200
    htmx = await client.get("/admin/static/htmx.min.js")
    assert htmx.status_code == 200 and htmx.content.startswith(b"var htmx")


async def test_no_page_loads_code_or_styles_from_another_host(authed, client):
    pages = [await home(authed), (await client.get("/admin/login")).text, (await authed.get("/admin/projects/new")).text]
    for page in pages:
        for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', page):
            assert "unpkg" not in url and "cdn" not in url and "googleapis" not in url, url
        for tag in re.findall(r"<(?:script|link)[^>]+>", page):
            assert not re.search(r'(?:src|href)="https?://', tag), tag


async def test_static_files_cannot_be_used_to_read_other_files(client):
    for path in ("/admin/static/../models.py", "/admin/static/%2e%2e/models.py", "/admin/static/..%2fconfig.py"):
        resp = await client.get(path)
        assert resp.status_code in (303, 404) and b"class Settings" not in resp.content


# --- the home page ---------------------------------------------------------------------------------


async def test_home_needs_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://admin.test") as visitor:
        resp = await visitor.get("/admin/")
        assert resp.status_code == 303 and resp.headers["location"] == "/login"


async def test_an_empty_site_invites_the_first_project(authed):
    page = await home(authed)
    assert "ยังไม่มีผลงาน" in page and 'href="/projects/new"' in page
    assert "ฐานข้อมูล ปกติ" in page and "ที่เก็บไฟล์ ปกติ" in page
    for expected in ("ผลงานที่เผยแพร่", "ประวัติการทำงาน", "บทความที่เผยแพร่", "รูปภาพทั้งหมด", "ในถังขยะ"):
        assert expected in page


async def test_the_counts_follow_the_content(authed):
    await add_category(authed)
    await add_tag(authed, "Rust")
    await add_project(authed, title_en="Live one")
    await add_project(authed, title_en="Draft one", status="draft")
    await add_project(authed, title_en="Hidden one", status="hidden")
    await add_work(authed, hidden="on")
    await add_article(authed)
    page = await home(authed)
    assert re.search(r'<div class="num[^"]*">1</div>\s*<div class="label[^"]*">ผลงานที่เผยแพร่</div>\s*<div class="sub[^"]*">ร่าง 1 · ถูกซ่อน 1</div>', page)
    assert re.search(r'<div class="num[^"]*">1</div>\s*<div class="label[^"]*">ประวัติการทำงาน</div>\s*<div class="sub[^"]*">ถูกซ่อน 1</div>', page)
    assert re.search(r'<div class="num[^"]*">1</div>\s*<div class="label[^"]*">บทความที่เผยแพร่</div>', page)
    assert "มีผลงานฉบับร่าง 1 ชิ้น" in page


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        ("stale", "ข้อมูลช่องถามตอบล้าสมัย"),
        ("draft_article", "มีบทความฉบับร่าง 1 ชิ้น"),
        ("no_image", "ผลงานที่เผยแพร่แล้วแต่ยังไม่มีรูป 1 ชิ้น"),
        ("gap", "ผลงานที่ยังแปลไม่ครบสองภาษา 1 รายการ"),
        ("trash", "มีของในถังขยะ 1 รายการ"),
        ("profile", "ข้อมูลส่วนตัวหน้าแรกยังไม่ครบ"),
        ("no_key", "ยังไม่ได้ตั้ง GEMINI_API_KEY"),
        ("unanswered", "มีคำถามที่ตอบไม่ได้ 1 ข้อใน 7 วันนี้"),
    ],
)
async def test_each_thing_that_needs_attention_is_listed_with_a_link(authed, setup, expected):
    await add_category(authed)
    if setup == "draft_article":
        await add_article(authed, status="draft")
    elif setup == "gap":
        await add_project(authed, title_th="", problem_th="")
    elif setup == "trash":
        await add_project(authed)
        await post(authed, "/admin/projects/1/trash")
    elif setup == "unanswered":
        await authed.post("/api/ask", json={"question": "what is the weather in paris today"})
    else:
        await add_project(authed)
    if setup not in ("stale",):
        await post(authed, "/admin/rag/rebuild")
    page = await home(authed)
    assert expected in page
    item = page.split(expected)[1].split("</li>")[0]
    assert re.search(r'<a class="[^"]*" href="/[^"]*">', item)  # each item says where to go


async def test_a_broken_storage_is_the_first_thing_shown(authed):
    app.dependency_overrides[__import__("app.storage", fromlist=["get_storage"]).get_storage] = lambda: Broken()
    page = await home(authed)
    assert "ที่เก็บไฟล์ไม่ตอบสนอง" in page and "ที่เก็บไฟล์ ไม่ตอบสนอง" in page
    first = re.search(r'<li(?: [^>]*)?>(.*?)</li>', page.split("<main")[1], re.S).group(1)
    assert "ควรทำ" in first and "ที่เก็บไฟล์ไม่ตอบสนอง" in first
    assert "ฐานข้อมูล ปกติ" in page  # the page still opens


async def test_a_long_to_do_list_is_folded(authed):
    await add_category(authed)
    await add_project(authed, title_th="", problem_th="")  # published, no picture, half translated, not indexed
    await add_project(authed, status="draft")
    await add_article(authed, status="draft")
    await add_project(authed)
    await post(authed, "/admin/projects/3/trash")
    page = await home(authed)
    content = page.split("<main")[1]  # the menus are lists too
    shown = content.split('<details class="todo-more')[0]
    assert len(re.findall(r"<li[ >]", shown)) == 6 and "ดูอีก" in page
    assert len(re.findall(r"<li[ >]", content)) >= 8  # the folded ones are still in the page, behind the summary


async def test_the_rebuild_shortcut_appears_only_when_the_index_is_stale(authed):
    await add_category(authed)
    await add_project(authed)
    assert 'action="/rag/rebuild"' in await home(authed)
    await post(authed, "/admin/rag/rebuild")
    assert 'action="/rag/rebuild"' not in await home(authed)


async def test_question_numbers_on_the_home_page(authed):
    await authed.post("/api/ask", json={"question": "hello"})
    await authed.post("/api/ask", json={"question": "what is the weather in paris today"})
    page = await home(authed)
    assert "ถาม <strong>2</strong> ครั้ง" in page and "เรียกโมเดล <strong>0</strong> ครั้ง" in page


# --- small interface details ------------------------------------------------------------------------


async def test_list_pages_use_the_toolbar_and_status_badges(authed):
    await add_category(authed)
    await add_project(authed, title_en="Published one")
    await add_project(authed, title_en="Draft one", status="draft")
    page = (await authed.get("/admin/projects")).text
    assert '/projects?trash=true' in page  # the toolbar links to the trash
    assert re.search(r'<a class="[^"]*btn-primary[^"]*" href="/projects/new"', page)  # the main action is marked
    assert re.search(r'<span class="[^"]*bg-success[^"]*">เผยแพร่</span>', page)  # published is green
    assert re.search(r'<span class="[^"]*bg-warning[^"]*">ร่าง</span>', page)  # a draft is amber
    trash = (await authed.get("/admin/projects?trash=true")).text
    assert "← กลับไปรายการ" in trash and "+ เพิ่มรายการ" not in trash


async def test_dangerous_buttons_are_marked(authed):
    await add_category(authed)
    await add_project(authed)
    await post(authed, "/admin/projects/1/trash")
    page = (await authed.get("/admin/trash")).text
    assert re.search(r'<button class="[^"]*btn-error[^"]*">ลบถาวร</button>', page)
    assert re.search(r'<button class="[^"]*btn-error[^"]*">ล้างถังขยะทั้งหมด', page)
    assert "confirm(" in page  # and each asks first


async def test_the_index_button_is_primary_when_the_index_is_out_of_date(authed):
    await add_category(authed)
    await add_project(authed)
    assert '<button class="primary">สร้างข้อมูลสำหรับค้นหาใหม่</button>' in (await authed.get("/admin/rag")).text
    await post(authed, "/admin/rag/rebuild")
    assert '<button>สร้างข้อมูลสำหรับค้นหาใหม่</button>' in (await authed.get("/admin/rag")).text
