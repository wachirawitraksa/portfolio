import math

from sqlalchemy import select

from app.db import SessionLocal
from app.models import EMBED_DIM, RagChunk
from app.rag.embed import embed
from app.rag.knowledge import expand, make_group
from app.rag.text import normalize, tokenize

from .test_articles import add_article
from .test_projects import add_category, add_project, add_tag
from .test_work import add_work


def vec(text):
    clean = normalize(text, limit=None)
    return embed(clean, tokenize(clean))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


async def post(c, path, **data):
    return await c.post(path, data={"csrf_token": c.csrf, **data})


async def chunks():
    async with SessionLocal() as db:
        return (await db.execute(select(RagChunk).order_by(RagChunk.id))).scalars().all()


# --- embedding --------------------------------------------------------------------------------


def test_embedding_is_unit_length_stable_and_sized():
    a = vec("ระบบสต็อกสินค้า stock system")
    assert len(a) == EMBED_DIM and math.isclose(dot(a, a), 1.0, rel_tol=1e-9)
    assert a == vec("ระบบสต็อกสินค้า stock system")  # same input, same vector, every run
    assert vec("") == [0.0] * EMBED_DIM


def test_similar_text_is_closer_than_unrelated_text():
    base = vec("ระบบจัดการสต็อกสินค้าด้วย PostgreSQL")
    near = vec("สต็อกสินค้า postgresql ระบบ")
    far = vec("แอปถ่ายรูปท่องเที่ยวบนมือถือ")
    assert dot(base, near) > dot(base, far) + 0.2
    assert dot(vec("inventory system in postgresql"), vec("postgresql inventory")) > dot(
        vec("inventory system in postgresql"), vec("holiday photo app")
    )


# --- glossary expansion -----------------------------------------------------------------------


def test_expand_adds_the_other_spellings_of_a_thing_the_question_mentions():
    groups = [make_group(["pg", "PostgreSQL", "postgres"]), make_group(["สต็อก", "stock", "inventory"])]
    query = normalize("pg สต็อกสินค้า")
    assert expand(query, tokenize(query), groups) == ["postgresql", "postgres", "stock", "inventory"]


def test_expand_ignores_groups_that_are_not_mentioned_and_terms_already_there():
    groups = [make_group(["pg", "postgresql"]), make_group(["docker", "container"])]
    query = normalize("tell me about pg and postgresql")
    assert expand(query, tokenize(query), groups) == []
    assert "pg" not in expand("xpgx", ["xpgx"], groups)  # a short term must match a whole word


def test_make_group_normalizes_and_drops_repeats_and_blanks():
    assert make_group(["PostgreSQL", "postgresql", " ", "x", "Postgres"]) == ["postgresql", "postgres"]


# --- glossary admin ---------------------------------------------------------------------------


async def test_glossary_crud_and_validation(authed):
    resp = await post(authed, "/admin/glossary", terms="สต็อก\nstock\ninventory", note="คลังสินค้า")
    assert resp.status_code == 303
    page = (await authed.get("/admin/glossary")).text
    assert "สต็อก = stock = inventory" in page and "คลังสินค้า" in page
    assert (await post(authed, "/admin/glossary", terms="onlyone")).status_code == 422
    assert (await post(authed, "/admin/glossary/1", terms="สต็อก, stock")).status_code == 303
    assert "สต็อก = stock" in (await authed.get("/admin/glossary")).text
    assert (await post(authed, "/admin/glossary/1", terms="x")).status_code == 422
    await post(authed, "/admin/glossary/1/trash")
    assert "ยังไม่มีกลุ่มคำ" in (await authed.get("/admin/glossary")).text
    assert "สต็อก" in (await authed.get("/admin/glossary?trash=true")).text
    await post(authed, "/admin/glossary/1/restore")
    assert "สต็อก" in (await authed.get("/admin/glossary")).text
    assert (await authed.get("/admin/glossary/new")).status_code == 200
    assert (await authed.get("/admin/glossary/1/edit")).status_code == 200
    assert (await authed.post("/admin/glossary", data={"terms": "a\nb"})).status_code == 403


# --- building the index -----------------------------------------------------------------------


async def seed(c):
    await add_category(c)
    await add_tag(c, "PostgreSQL", "pg")
    await add_project(
        c,
        title_th="ระบบสต็อก",
        title_en="Stock system",
        problem_th="นับของด้วยมือ",
        problem_en="Counting by hand",
        work_th="เขียน API",
        work_en="Wrote the API",
        result_en="Counting went from 8 minutes to 40 seconds",
        repo_url="https://github.com/me/stock",
        aliases="สต็อกของร้าน\nคลังสินค้า",
        tag_ids=["1"],
        year="2025",
    )
    await add_project(c, title_en="Secret draft", status="draft")
    await add_project(c, title_en="Hidden one", status="hidden")
    await add_work(c, employer="Acme", position_en="Backend Engineer", tag_ids=["1"])
    await add_work(c, employer="Nowhere", hidden="on")
    await add_article(c, title_en="Why Postgres", body_en="First paragraph.\n\nSecond paragraph.")
    await add_article(c, title_en="Draft article", status="draft")
    await post(c, "/admin/profile", name_th="อาร์ม", name_en="Arm", intro_en="I build things", email="arm@example.com")
    await post(c, "/admin/profile/links", label="GitHub", url="https://github.com/arm")


async def test_rebuild_indexes_only_what_is_public(authed):
    await seed(authed)
    resp = await post(authed, "/admin/rag/rebuild")
    assert resp.status_code == 303 and resp.headers["location"] == "/rag?done=true"
    rows = await chunks()
    kinds = sorted({r.source_type for r in rows})
    assert kinds == ["article", "profile", "project", "work"]
    text = " ".join(r.title_en + r.search_text for r in rows)
    assert "secret draft" not in text and "hidden one" not in text and "nowhere" not in text
    assert "draft article" not in text


async def test_chunks_carry_both_languages_aliases_tags_and_links(authed):
    await seed(authed)
    await post(authed, "/admin/rag/rebuild")
    project = [r for r in await chunks() if r.source_type == "project"]
    assert {r.section for r in project} == {"overview", "work", "result"}  # empty sections make no chunk
    overview = next(r for r in project if r.section == "overview")
    assert "นับของด้วยมือ" in overview.body_th and "Counting by hand" in overview.body_en
    assert "https://github.com/me/stock" in overview.body_en and "PostgreSQL" in overview.body_en
    for chunk in project:  # an alias, a tag name and a tag alias find every chunk of the project
        assert "คลังสินค้า" in chunk.search_text and "postgresql" in chunk.search_text and "pg" in chunk.search_text.split()
        assert len(chunk.embedding) == EMBED_DIM and chunk.sound


async def test_work_article_and_profile_chunks(authed):
    await seed(authed)
    await post(authed, "/admin/rag/rebuild")
    rows = await chunks()
    job = next(r for r in rows if r.source_type == "work")
    assert "Backend Engineer (Acme)" == job.title_en and "2023-03-15 – 2025-06-30" in job.body_en
    assert "• Built a stock system" in job.body_en and "งานประจำ" in job.body_th
    article = [r for r in rows if r.source_type == "article"]
    assert [r.section for r in article] == ["summary", "body1"]
    assert "Second paragraph." in article[1].body_en
    about = next(r for r in rows if r.source_type == "profile")
    assert "Arm" in about.body_en and "arm@example.com" in about.body_en and "https://github.com/arm" in about.body_en


async def test_long_article_body_is_split_into_chunks(authed):
    paragraphs = "\n\n".join(f"Paragraph number {n} " + "word " * 120 for n in range(6))
    await add_article(authed, body_en=paragraphs, body_th="")
    await post(authed, "/admin/rag/rebuild")
    parts = [r for r in await chunks() if r.section.startswith("body")]
    assert len(parts) >= 3 and all(len(p.body_en) < 1800 for p in parts)


async def test_rebuild_replaces_everything_and_follows_content_changes(authed):
    await seed(authed)
    await post(authed, "/admin/rag/rebuild")
    first = len(await chunks())
    await post(authed, "/admin/rag/rebuild")
    assert len(await chunks()) == first  # replaced, not appended
    await post(authed, "/admin/projects/1/trash")
    await post(authed, "/admin/rag/rebuild")
    assert all(r.source_id != 1 for r in await chunks() if r.source_type == "project")


async def test_rebuild_on_an_empty_site_leaves_no_chunks(authed):
    await post(authed, "/admin/rag/rebuild")
    assert await chunks() == []
    assert "ยังไม่มีข้อมูล" in (await authed.get("/admin/rag")).text


async def test_rag_admin_page_shows_counts(authed):
    await seed(authed)
    await post(authed, "/admin/rag/rebuild")
    page = (await authed.get("/admin/rag?done=true")).text
    assert "สร้างข้อมูลสำหรับค้นหาใหม่แล้ว" in page and "ผลงาน: 3" in page and "ประวัติการทำงาน: 1" in page
    assert (await authed.post("/admin/rag/rebuild", data={})).status_code == 403
