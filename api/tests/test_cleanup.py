from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from app.db import SessionLocal
from app.models import ContactLink, GlossaryEntry, Kind, Project, ProjectImage, RagQuery, Tag
from app.rag.ask import purge_old_queries
from app.rag.index import index_status

from .test_articles import add_article
from .test_images import PNG, upload
from .test_projects import add_category, add_project, add_tag, public
from .test_work import add_work


async def post(c, path, **data):
    return await c.post(path, data={"csrf_token": c.csrf, **data})


async def count(model):
    async with SessionLocal() as db:
        return (await db.execute(select(func.count()).select_from(model))).scalar_one()


async def trash_page(c, query=""):
    return (await c.get(f"/admin/trash{query}")).text


# --- the trash page --------------------------------------------------------------------------


async def test_empty_trash(authed):
    page = await trash_page(authed)
    assert "ถังขยะว่างอยู่" in page and "ล้างถังขยะทั้งหมด" not in page


async def seed_trash(c):
    """One trashed item of every kind."""
    await add_category(c)
    await post(c, "/admin/kinds", name_th="ชนิดทดสอบ", name_en="Test kind")
    await add_tag(c, "Rust", "rs")
    await add_project(c, title_th="ผลงานที่ลบ", title_en="Trashed project")
    await upload(c, 1, ("a.png", PNG))
    await add_work(c, employer="Acme", position_en="Trashed job", position_th="")  # the page shows Thai first
    await add_article(c, title_en="Trashed article", title_th="")
    await post(c, "/admin/glossary", terms="ก\nข")
    await post(c, "/admin/profile/links", label="Old site", url="https://example.com")
    await post(c, "/admin/projects/1/images/1/trash")
    for path in ("projects/1", "kinds/1", "tags/1", "work/1", "articles/1", "glossary/1", "profile/links/1"):
        await post(c, f"/admin/{path}/trash")
    await add_project(c, title_en="Spare", category_ids=["1"])  # keeps category 1 in use...
    await post(c, "/admin/categories", name_th="ประเภทว่าง", name_en="Empty one")
    await post(c, "/admin/categories/2/trash")  # ...so this unused one is the one that can be trashed


async def test_the_page_lists_every_kind_of_trashed_item(authed):
    await seed_trash(authed)
    page = await trash_page(authed)
    for expected in (
        "ผลงานที่ลบ", "รูป #1", "Trashed job", "Trashed article", "ประเภทว่าง", "ชนิดทดสอบ", "Rust", "ก = ข", "Old site",
        "ผลงาน / ใบเซอร์ / รายการ", "ประวัติการทำงาน", "tag เทคโนโลยี", "ล้างถังขยะทั้งหมด (9)",
    ):
        assert expected in page, expected
    assert "Spare" not in page  # live items are not in the trash


# --- restore ---------------------------------------------------------------------------------


async def test_restore_brings_items_back_hidden_where_visitors_would_see_them(authed):
    await seed_trash(authed)
    for kind, item in (("project", 1), ("work", 1), ("article", 1), ("image", 1)):
        resp = await post(authed, "/admin/trash/restore", kind=kind, item_id=str(item))
        assert resp.status_code == 303 and resp.headers["location"] == "/trash?restored=true"
    assert "Trashed project" not in await trash_page(authed)
    async with SessionLocal() as db:
        assert (await db.get(Project, 1)).status == "hidden"
    assert (await authed.get("/api/projects/1")).status_code == 404  # not public until reviewed
    assert await public(authed, "/api/experience") == []
    assert (await public(authed, "/api/articles"))["total"] == 0
    async with SessionLocal() as db:
        image = await db.get(ProjectImage, 1)
        assert image.deleted_at is None and image.is_cover  # the only image becomes the cover again


async def test_restore_refuses_unknown_kinds_and_items_that_are_not_in_the_trash(authed):
    await seed_trash(authed)
    assert (await post(authed, "/admin/trash/restore", kind="nonsense", item_id="1")).status_code == 404
    assert (await post(authed, "/admin/trash/restore", kind="project", item_id="2")).status_code == 404  # live
    assert (await post(authed, "/admin/trash/restore", kind="project", item_id="999")).status_code == 404


# --- deleting for good -----------------------------------------------------------------------


async def test_deleting_a_project_for_good_removes_its_files_too(authed, storage):
    await add_category(authed)
    await add_project(authed, title_en="Goner")
    await add_project(authed, title_en="Keeper")
    await upload(authed, 1, ("a.png", PNG), ("b.png", PNG))
    await upload(authed, 2, ("c.png", PNG))
    await authed.post("/admin/settings", data={
        "csrf_token": authed.csrf, "featured_limit": "6", "projects_page_size": "12",
        "articles_page_size": "12", "how_i_work_project_id": "1",
    })
    assert len(storage.files) == 3
    await post(authed, "/admin/projects/1/trash")
    resp = await post(authed, "/admin/trash/delete", kind="project", item_id="1")
    assert resp.headers["location"] == "/trash?deleted=1&skipped=0"
    assert len(storage.files) == 1 and all(key.startswith("projects/2/") for key in storage.files)
    async with SessionLocal() as db:
        assert await db.get(Project, 1) is None
        assert (await db.execute(select(func.count()).select_from(ProjectImage).where(ProjectImage.project_id == 1))).scalar_one() == 0
        assert (await db.get(Project, 2)).title_en == "Keeper"
    assert (await public(authed, "/api/settings"))["how_i_work_project_id"] is None  # the setting let go of it
    assert "ลบถาวรแล้ว 1 รายการ" in await trash_page(authed, "?deleted=1&skipped=0")


async def test_only_items_already_in_the_trash_can_be_deleted_for_good(authed, storage):
    await add_category(authed)
    await add_project(authed, title_en="Alive")
    await upload(authed, 1, ("a.png", PNG))
    assert (await post(authed, "/admin/trash/delete", kind="project", item_id="1")).status_code == 404
    assert (await post(authed, "/admin/trash/delete", kind="image", item_id="1")).status_code == 404
    assert (await post(authed, "/admin/trash/delete", kind="bogus", item_id="1")).status_code == 404
    assert await count(Project) == 1 and len(storage.files) == 1


async def test_deleting_an_image_for_good_removes_only_that_file(authed, storage):
    await add_category(authed)
    await add_project(authed)
    await upload(authed, 1, ("a.png", PNG), ("b.png", PNG))
    await post(authed, "/admin/projects/1/images/1/trash")
    await post(authed, "/admin/trash/delete", kind="image", item_id="1")
    assert len(storage.files) == 1 and await count(ProjectImage) == 1
    assert [i["id"] for i in (await public(authed, "/api/projects/1"))["images"]] == [2]


async def test_deleting_a_tag_for_good_unlinks_it_from_projects(authed):
    await add_category(authed)
    await add_tag(authed, "Rust")
    await add_project(authed, tag_ids=["1"])
    await post(authed, "/admin/tags/1/trash")
    await post(authed, "/admin/trash/delete", kind="tag", item_id="1")
    assert await count(Tag) == 0
    assert (await public(authed, "/api/projects/1"))["tags"] == []


async def test_a_kind_still_in_use_is_skipped_not_lost(authed):
    await post(authed, "/admin/kinds", name_th="ชนิดใช้อยู่", name_en="In use")
    await add_category(authed)
    await add_project(authed, kind_id="1")
    async with SessionLocal() as db:  # trashed behind the app's back, so the usual "in use" guard did not run
        await db.execute(text("update kind set deleted_at = now() where id = 1"))
        await db.commit()
    resp = await post(authed, "/admin/trash/delete", kind="kind", item_id="1")
    assert resp.headers["location"] == "/trash?deleted=0&skipped=1"
    async with SessionLocal() as db:
        assert (await db.get(Kind, 1)) is not None
    assert "ข้าม 1 รายการ" in await trash_page(authed, "?deleted=0&skipped=1")


async def test_empty_one_kind_or_everything(authed, storage):
    await seed_trash(authed)
    resp = await post(authed, "/admin/trash/empty", kind="project")
    assert resp.headers["location"] == "/trash?deleted=1&skipped=0"
    assert not storage.files  # the project's trashed image went with it
    page = await trash_page(authed)
    assert "Trashed project" not in page and "Trashed article" in page  # other kinds untouched
    assert (await post(authed, "/admin/trash/empty", kind="all")).status_code == 303
    assert "ถังขยะว่างอยู่" in await trash_page(authed)
    assert await count(GlossaryEntry) == 0 and await count(ContactLink) == 0 and await count(Tag) == 0
    async with SessionLocal() as db:  # live things survive
        assert [p.title_en for p in (await db.execute(select(Project))).scalars()] == ["Spare"]


async def test_trash_needs_login_and_csrf(authed):
    await seed_trash(authed)
    for path, data in (("/admin/trash/restore", {"kind": "project", "item_id": "1"}),
                       ("/admin/trash/delete", {"kind": "project", "item_id": "1"}),
                       ("/admin/trash/empty", {"kind": "all"})):
        assert (await authed.post(path, data=data)).status_code == 403
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://admin.test") as visitor:
        assert (await visitor.get("/admin/trash")).status_code == 303
        assert (await visitor.post("/admin/trash/empty", data={"kind": "all"})).status_code == 303
    assert await count(Project) == 2  # nothing was deleted


# --- the question log ------------------------------------------------------------------------


async def add_logged(days_old: int, question: str = "q"):
    async with SessionLocal() as db:
        db.add(RagQuery(question=question, created_at=datetime.now(timezone.utc) - timedelta(days=days_old), mode="no_answer"))
        await db.commit()


async def test_old_questions_are_deleted_and_recent_ones_kept(authed):
    await add_logged(120, "old"), await add_logged(10, "recent")
    async with SessionLocal() as db:
        assert await purge_old_queries(db) == 1  # the default is 90 days
    async with SessionLocal() as db:
        assert [q.question for q in (await db.execute(select(RagQuery))).scalars()] == ["recent"]


async def test_the_retention_period_is_a_setting(authed, monkeypatch):
    monkeypatch.setenv("ASK_LOG_DAYS", "5")
    await add_logged(7, "week old"), await add_logged(2, "fresh")
    async with SessionLocal() as db:
        assert await purge_old_queries(db) == 1


async def test_asking_sometimes_sweeps_the_old_log(authed, monkeypatch):
    await add_logged(200, "ancient")
    monkeypatch.setattr("app.rag.ask.random.random", lambda: 0.0)  # force the sweep
    assert (await authed.post("/api/ask", json={"question": "hello"})).status_code == 200
    async with SessionLocal() as db:
        assert [q.question for q in (await db.execute(select(RagQuery))).scalars()] == ["hello"]


async def test_asking_does_not_always_sweep(authed, monkeypatch):
    await add_logged(200, "ancient")
    monkeypatch.setattr("app.rag.ask.random.random", lambda: 0.99)
    await authed.post("/api/ask", json={"question": "hello"})
    assert await count(RagQuery) == 2


async def test_admin_can_delete_old_or_all_logged_questions(authed):
    await add_logged(120, "old"), await add_logged(1, "recent")
    page = (await authed.get("/admin/rag/questions?show=all")).text
    assert "เก็บล็อก 90 วัน" in page and "ตอนนี้มี 2 รายการ" in page
    resp = await post(authed, "/admin/rag/questions/purge", scope="old")
    assert resp.headers["location"] == "/rag/questions?purged=1"
    assert "ลบล็อกแล้ว 1 รายการ" in (await authed.get("/admin/rag/questions?purged=1")).text
    assert await count(RagQuery) == 1
    await post(authed, "/admin/rag/questions/purge", scope="all")
    assert await count(RagQuery) == 0
    assert (await authed.post("/admin/rag/questions/purge", data={"scope": "all"})).status_code == 403


# --- is the search index out of date? --------------------------------------------------------


async def status():
    async with SessionLocal() as db:
        return await index_status(db)


async def test_no_content_and_no_index_is_not_stale(authed):
    assert await status() == {"stale": False, "added": 0, "removed": 0, "changed": 0, "built": False}


async def test_new_content_makes_the_index_stale_until_rebuilt(authed):
    await add_category(authed)
    await add_project(authed, title_en="First", work_en="Did things")
    found = await status()
    assert found["stale"] and found["added"] == 2 and found["built"] is False  # overview + work
    assert "เนื้อหาเปลี่ยนไปหลังสร้างครั้งล่าสุด" in (await authed.get("/admin/rag")).text
    await post(authed, "/admin/rag/rebuild")
    assert (await status())["stale"] is False
    page = (await authed.get("/admin/rag")).text
    assert "ข้อมูลตรงกับเนื้อหาปัจจุบันแล้ว" in page and "เนื้อหาเปลี่ยนไป" not in page


async def test_edits_removals_and_hidden_content_are_noticed(authed):
    await add_category(authed)
    await add_project(authed, title_en="First", work_en="Did things")
    await post(authed, "/admin/rag/rebuild")
    await authed.post("/admin/projects/1", data={"csrf_token": authed.csrf, "title_en": "Renamed", "work_en": "Did things", "status": "published"})
    assert (await status())["changed"] >= 1
    await post(authed, "/admin/rag/rebuild")
    await post(authed, "/admin/projects/1/trash")
    after = await status()
    assert after["stale"] and after["removed"] == 2 and after["added"] == 0
    page = (await authed.get("/admin/rag")).text
    assert "ลบ 2" in page


async def test_a_draft_does_not_make_the_index_stale(authed):
    await add_category(authed)
    await add_project(authed, title_en="Live")
    await post(authed, "/admin/rag/rebuild")
    await add_project(authed, title_en="Draft", status="draft")
    assert (await status())["stale"] is False  # drafts are never indexed
