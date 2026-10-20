import re

from sqlalchemy import select

from app.db import SessionLocal
from app.models import EducationEntry
from app.rag.search import retrieve

from .test_projects import public


def edu_data(c, **overrides):
    data = {
        "institution_th": "จุฬาลงกรณ์มหาวิทยาลัย",
        "institution_en": "Chulalongkorn University",
        "level": "bachelor",
        "degree_th": "วิศวกรรมศาสตรบัณฑิต",
        "degree_en": "B.Eng.",
        "field_th": "วิศวกรรมคอมพิวเตอร์",
        "field_en": "Computer Engineering",
        "grade": "GPA 3.45",
        "span": "range",
        "started_on": "2015-06",
        "ended_on": "2019-05",
        "details_th": "โครงงานระบบสต็อก\nเกียรตินิยมอันดับสอง",
        "details_en": "Stock system capstone\nSecond-class honors",
        "csrf_token": c.csrf,
    }
    data.update(overrides)
    return data


async def add_edu(c, **overrides):
    return await c.post("/admin/education", data=edu_data(c, **overrides))


async def post(c, path):
    return await c.post(path, data={"csrf_token": c.csrf})


async def ask(question):
    async with SessionLocal() as db:
        return await retrieve(db, question)


async def test_create_shows_in_admin_and_public_api(authed):
    assert (await add_edu(authed)).status_code == 303
    page = (await authed.get("/admin/education")).text
    assert "Chulalongkorn University" in page and "2015-06 – 2019-05" in page and "ปริญญาตรี" in page
    item = (await public(authed, "/api/education"))[0]
    assert item["institution_en"] == "Chulalongkorn University" and item["degree_en"] == "B.Eng."
    assert item["level"] == "bachelor" and item["level_th"] == "ปริญญาตรี" and item["level_en"] == "Bachelor's degree"
    assert item["span"] == "range" and item["started_on"] == "2015-06" and item["ended_on"] == "2019-05"
    assert item["grade"] == "GPA 3.45" and item["details_en"] == ["Stock system capstone", "Second-class honors"]


async def test_still_studying_has_no_end_and_ignores_a_typed_end_month(authed):
    await add_edu(authed, span="ongoing", ended_on="2030-01", level="master")
    item = (await public(authed, "/api/education"))[0]
    assert item["span"] == "ongoing" and item["ended_on"] is None
    assert "ปัจจุบัน" in (await authed.get("/admin/education")).text


async def test_newest_first(authed):
    await add_edu(authed, institution_en="Older", started_on="2010-06", ended_on="2014-05")
    await add_edu(authed, institution_en="Newer", started_on="2019-06", ended_on="2021-05", level="master")
    assert [i["institution_en"] for i in await public(authed, "/api/education")] == ["Newer", "Older"]


async def test_only_one_language_is_enough(authed):
    assert (await add_edu(authed, institution_en="", degree_en="", field_en="", details_en="")).status_code == 303
    assert (await add_edu(authed, institution_th="", degree_th="", field_th="", details_th="")).status_code == 303
    assert len(await public(authed, "/api/education")) == 2


async def test_validation_errors_keep_the_form(authed):
    for override, message in (
        ({"institution_th": "", "institution_en": ""}, "ต้องกรอกชื่อสถาบัน"),
        ({"started_on": ""}, "ต้องเลือกเดือนที่เริ่มเรียน"),
        ({"ended_on": ""}, "ต้องเลือกเดือนที่สิ้นสุด"),
        ({"started_on": "2019-05", "ended_on": "2015-01"}, "ต้องไม่ก่อนเดือนที่เริ่ม"),
        ({"started_on": "not-a-month"}, "ต้องเลือกเดือนที่เริ่มเรียน"),
        ({"level": "bogus"}, "ระดับการศึกษาไม่ถูกต้อง"),
        ({"span": "bogus"}, "ช่วงเวลาไม่ถูกต้อง"),
    ):
        resp = await add_edu(authed, **override)
        assert resp.status_code == 422 and message in resp.text, override
    assert await public(authed, "/api/education") == []


async def test_hide_edit_trash_restore(authed):
    await add_edu(authed)
    await post(authed, "/admin/education/1/hide")
    assert await public(authed, "/api/education") == []
    await post(authed, "/admin/education/1/hide")
    assert len(await public(authed, "/api/education")) == 1
    await authed.post("/admin/education/1", data=edu_data(authed, institution_en="Renamed", span="ongoing"))
    item = (await public(authed, "/api/education"))[0]
    assert item["institution_en"] == "Renamed" and item["span"] == "ongoing"
    await post(authed, "/admin/education/1/trash")
    assert await public(authed, "/api/education") == []
    assert "Renamed" in (await authed.get("/admin/education?trash=true")).text
    await post(authed, "/admin/education/1/restore")
    assert await public(authed, "/api/education") == []  # back hidden until reviewed


async def test_untranslated_flag_and_form_pages(authed):
    await add_edu(authed, degree_en="")
    assert "ยังไม่ได้แปล 1 ช่อง" in (await authed.get("/admin/education")).text
    new = (await authed.get("/admin/education/new")).text
    assert 'name="span"' in new and 'value="bachelor" selected' in new
    edit = (await authed.get("/admin/education/1/edit")).text
    assert 'value="range" checked' in edit and 'value="2019-05"' in edit and "GPA 3.45" in edit
    assert (await authed.get("/admin/education/99/edit")).status_code == 404


async def test_mutations_need_csrf_and_login(authed):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    assert (await authed.post("/admin/education", data={"institution_en": "x"})).status_code == 403
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://admin.test") as visitor:
        assert (await visitor.get("/admin/education")).status_code == 303


async def test_the_menu_dashboard_and_trash_know_about_education(authed):
    await add_edu(authed, degree_en="")
    page = (await authed.get("/admin/education")).text
    assert re.search(r'<a href="/education"[^>]*aria-current="page"', page)
    home = (await authed.get("/admin/")).text
    assert re.search(r'<div class="num">1</div>\s*<div class="label">ประวัติการศึกษา</div>', home)
    assert "ประวัติการศึกษาที่ยังแปลไม่ครบสองภาษา 1 รายการ" in home
    await post(authed, "/admin/education/1/trash")
    trash = (await authed.get("/admin/trash")).text
    assert "ประวัติการศึกษา" in trash and "Chulalongkorn" not in trash and "จุฬาลงกรณ์มหาวิทยาลัย (วิศวกรรมคอมพิวเตอร์)" in trash
    await authed.post("/admin/trash/restore", data={"csrf_token": authed.csrf, "kind": "education", "item_id": "1"})
    async with SessionLocal() as db:
        row = (await db.execute(select(EducationEntry))).scalar_one()
        assert row.deleted_at is None and row.hidden is True  # restored hidden
    await post(authed, "/admin/education/1/trash")
    await authed.post("/admin/trash/delete", data={"csrf_token": authed.csrf, "kind": "education", "item_id": "1"})
    async with SessionLocal() as db:
        assert (await db.execute(select(EducationEntry))).scalars().all() == []


# --- the question box ---------------------------------------------------------------------------------


async def test_index_includes_visible_education_in_both_languages(authed):
    await add_edu(authed)
    await add_edu(authed, institution_en="Hidden school", institution_th="โรงเรียนซ่อน", hidden="on")
    assert (await authed.post("/admin/rag/rebuild", data={"csrf_token": authed.csrf})).status_code == 303
    from app.models import RagChunk

    async with SessionLocal() as db:
        chunks = (await db.execute(select(RagChunk).where(RagChunk.source_type == "education"))).scalars().all()
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.title_en == "B.Eng. Computer Engineering (Chulalongkorn University)"
    assert "GPA 3.45" in chunk.body_en and "• Second-class honors" in chunk.body_en and "2015-06 – 2019-05" in chunk.body_en
    assert "วิศวกรรมศาสตรบัณฑิต" in chunk.body_th and "ปริญญาตรี" in chunk.body_th
    assert "hidden school" not in chunk.search_text and "โรงเรียนซ่อน" not in chunk.search_text


async def test_questions_about_studies_find_the_education_entry(authed):
    await add_edu(authed)
    await authed.post("/admin/rag/rebuild", data={"csrf_token": authed.csrf})
    for question in ("where did you study", "ประวัติการศึกษา", "จบมหาวิทยาลัยอะไร", "what degree do you have", "Chulalongkorn"):
        found = await ask(question)
        assert found.hits and (found.hits[0].chunk.source_type, found.hits[0].chunk.source_id) == ("education", 1), question
        assert found.band in ("high", "medium"), question


async def test_the_ask_endpoint_cites_education_as_a_source(authed):
    await add_edu(authed)
    await authed.post("/admin/rag/rebuild", data={"csrf_token": authed.csrf})
    body = (await authed.post("/api/ask", json={"question": "what degree do you have"})).json()
    assert body["sources"][0]["type"] == "education" and body["mode"] in ("fallback", "answer", "uncertain")


async def test_index_status_notices_education_changes(authed):
    from app.rag.index import index_status

    await add_edu(authed)
    async with SessionLocal() as db:
        assert (await index_status(db))["added"] == 1
    await authed.post("/admin/rag/rebuild", data={"csrf_token": authed.csrf})
    async with SessionLocal() as db:
        assert (await index_status(db))["stale"] is False
    await authed.post("/admin/education/1", data=edu_data(authed, grade="GPA 3.80"))
    async with SessionLocal() as db:
        assert (await index_status(db))["changed"] == 1
