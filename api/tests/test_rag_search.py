import pytest

from app.db import SessionLocal
from app.rag.search import retrieve
from app.rag.text import THAI_TO_LATIN

from .test_articles import add_article
from .test_projects import add_category, add_project, add_tag
from .test_work import add_work


async def post(c, path, **data):
    return await c.post(path, data={"csrf_token": c.csrf, **data})


async def ask(question):
    async with SessionLocal() as db:
        return await retrieve(db, question)


def where(result):
    return [(h.chunk.source_type, h.chunk.source_id, h.chunk.section) for h in result.hits]


def sources(result):
    return [(h.chunk.source_type, h.chunk.source_id) for h in result.hits]


@pytest.fixture
async def site(authed):
    """A small bilingual site: two projects, a job, an article and a profile, already indexed."""
    await add_category(authed)
    await add_tag(authed, "PostgreSQL", "pg")
    await add_tag(authed, "Flutter")
    await add_project(
        authed,
        title_th="ระบบสต็อกสินค้า",
        title_en="Stock system",
        problem_th="ร้านค้านับของด้วยมือทุกสัปดาห์",
        problem_en="Shops counted goods by hand every week",
        work_th="เขียน API และฐานข้อมูล",
        work_en="Wrote the API and the database",
        result_en="Counting went from 8 minutes to 40 seconds",
        result_th="เวลานับลดจาก 8 นาทีเหลือ 40 วินาที",
        aliases="คลังสินค้า",
        tag_ids=["1"],
    )
    await add_project(
        authed,
        title_th="แอปถ่ายรูปท่องเที่ยว",
        title_en="Travel photo app",
        problem_th="คนอยากแชร์รูปทริปบนมือถือ",
        problem_en="People wanted to share trip photos on their phone",
        tag_ids=["2"],
    )
    await add_project(authed, title_en="Secret draft", status="draft", problem_en="launch codes")
    await add_work(
        authed,
        employer="Acme",
        position_th="วิศวกรซอฟต์แวร์",
        position_en="Backend Engineer",
        bullets_th="ประสบการณ์ทำงานด้านระบบหลังบ้าน",
        bullets_en="Backend systems experience",
        tag_ids=["1"],
    )
    await add_article(authed, title_en="Why Postgres", summary_en="Notes on choosing a database")
    await post(authed, "/admin/profile", name_th="อาร์ม", name_en="Arm", intro_en="I build software", intro_th="ผมสร้างซอฟต์แวร์")
    await post(authed, "/admin/rag/rebuild")
    return authed


async def test_a_thai_question_finds_the_matching_project(site):
    result = await ask("ระบบสต็อกสินค้าแก้ปัญหาอะไร")
    assert sources(result)[0] == ("project", 1)
    assert result.band == "high" and result.top >= 0.5


async def test_an_english_question_finds_the_thai_titled_project(site):
    result = await ask("tell me about the stock system")
    assert sources(result)[0] == ("project", 1) and result.band in ("high", "medium")


async def test_a_question_in_the_other_language_than_the_content_still_matches(site):
    assert ("project", 2) in sources(await ask("ถ่ายรูป"))  # Thai question, project 2 has Thai text
    assert sources(await ask("travel photo"))[0] == ("project", 2)


async def test_glossary_bridges_different_words_for_the_same_thing(site):
    before = await ask("inventory")
    assert before.prepared.expansions == []
    await post(site, "/admin/glossary", terms="inventory\nstock\nสต็อก")
    after = await ask("inventory")
    assert {"stock", "สต็อก"} <= set(after.prepared.expansions)
    assert sources(after)[0] == ("project", 1)  # takes effect without a rebuild
    assert after.top > before.top


async def test_tag_alias_works_without_any_glossary_entry(site):
    result = await ask("pg")
    assert "postgresql" in result.prepared.expansions
    assert ("project", 1) in sources(result) and ("work", 1) in sources(result)


async def test_project_alias_finds_the_project(site):
    result = await ask("คลังสินค้า")
    assert sources(result)[0] == ("project", 1) and result.band == "high"


async def test_typos_still_find_it(site):
    result = await ask("stok sytem")
    assert ("project", 1) in sources(result)[:3] and result.band in ("high", "medium")


async def test_thai_typed_on_the_english_keyboard(site):
    typed = "".join(THAI_TO_LATIN[c] for c in "สต็อก")  # the keys that spell สต็อก on a Thai keyboard
    assert typed == "l9Hvd"
    result = await ask(typed)
    assert result.prepared.keyboard_fixed and result.prepared.text == "สต็อก"
    assert sources(result)[0] == ("project", 1)
    assert (await ask("z]'ko")).prepared.text == "ผลงาน"  # punctuation keys are Thai letters too


async def test_stock_typed_on_the_thai_keyboard_finds_the_project(site):
    result = await ask("หะนแา")  # "stock" typed with a Thai keyboard
    assert result.prepared.keyboard_fixed and result.prepared.text == "stock"
    assert sources(result)[0] == ("project", 1)


async def test_thai_typed_in_latin_letters_is_matched_by_sound(site):
    result = await ask("prasopkan tam ngan")  # "ประสบการณ์ทำงาน"
    assert result.prepared.sound
    assert ("work", 1) in sources(result)[:3]
    assert max(h.sound for h in result.hits) > 0.3


async def test_broad_questions_reach_the_right_kind_of_content(site):
    projects = await ask("what projects do you have")
    assert {s[0] for s in sources(projects)} == {"project"} and projects.band in ("high", "medium")
    assert {("project", 1), ("project", 2)} <= set(sources(projects))
    assert sources(await ask("tell me about yourself"))[0] == ("profile", 1)
    assert sources(await ask("how can I contact you"))[0] == ("profile", 1)
    assert sources(await ask("แนะนำตัวหน่อย"))[0] == ("profile", 1)
    assert sources(await ask("ประสบการณ์ทำงาน"))[0][0] == "work"
    assert sources(await ask("do you write articles"))[0][0] == "article"


async def test_off_topic_questions_have_low_confidence(site):
    for question in ("what is the weather in paris today", "ราคาทองวันนี้เท่าไหร่", "how tall is mount everest"):
        result = await ask(question)
        assert result.band == "low", (question, result.top)


async def test_gibberish_empty_and_symbols_do_not_crash(site):
    for question in ("", "   ", "???", "!!!!", "ฟหกดฟหกดฟหกด", "a", "'; drop table rag_chunk; --", "%_\\"):
        result = await ask(question)
        assert result.band in ("low", "medium")
    assert "launch codes" not in str([h.chunk.search_text for h in (await ask("launch codes")).hits])


async def test_unpublished_content_is_never_found(site):
    result = await ask("secret draft launch codes")
    assert ("project", 3) not in sources(result)


async def test_no_more_than_two_chunks_per_source(site):
    result = await ask("stock system")
    per_source = {}
    for source in sources(result):
        per_source[source] = per_source.get(source, 0) + 1
    assert max(per_source.values()) <= 2 and len(result.hits) <= 5


async def test_hits_are_sorted_and_scores_are_in_range(site):
    result = await ask("stock system database")
    scores = [h.score for h in result.hits]
    assert scores == sorted(scores, reverse=True) and all(0 <= s <= 1 for s in scores)


async def test_an_empty_index_finds_nothing(authed):
    result = await ask("anything at all")
    assert result.hits == [] and result.band == "low"


async def test_admin_try_page_shows_confidence_and_matches(site):
    page = (await site.get("/admin/rag?q=stock+system")).text
    assert "ความมั่นใจ" in page and "project#1" in page
    keyboard = (await site.get("/admin/rag", params={"q": "หะนแา"})).text
    assert "แก้แป้นพิมพ์เป็น: stock" in keyboard
    assert "ไม่พบข้อมูล" in (await site.get("/admin/rag?q=weather+in+paris")).text
