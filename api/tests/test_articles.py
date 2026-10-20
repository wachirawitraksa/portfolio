from .test_projects import add_tag, public


def article_data(c, **overrides):
    data = {
        "title_th": "ทำไมต้อง Postgres",
        "title_en": "Why Postgres",
        "summary_th": "สรุป",
        "summary_en": "Summary",
        "body_th": "# เนื้อหา",
        "body_en": "# Body",
        "source": "internal",
        "published_on": "2026-03-01",
        "status": "published",
        "csrf_token": c.csrf,
    }
    data.update(overrides)
    return data


async def add_article(c, **overrides):
    return await c.post("/admin/articles", data=article_data(c, **overrides))


async def test_internal_article_in_admin_and_public_api(authed):
    assert (await add_article(authed)).status_code == 303
    assert "Why Postgres" in (await authed.get("/admin/articles")).text
    body = await public(authed, "/api/articles")
    assert body["total"] == 1
    card = body["items"][0]
    assert card["title_en"] == "Why Postgres" and card["source"] == "internal"
    assert "body_en" not in card
    detail = await public(authed, "/api/articles/1")
    assert detail["body_en"] == "# Body" and detail["published_on"] == "2026-03-01"


async def test_external_article_keeps_link_and_drops_body(authed):
    resp = await add_article(
        authed,
        source="external",
        external_url="https://medium.com/@me/post",
        platform="Medium",
    )
    assert resp.status_code == 303
    detail = await public(authed, "/api/articles/1")
    assert detail["source"] == "external" and detail["platform"] == "Medium"
    assert detail["external_url"] == "https://medium.com/@me/post"
    assert detail["body_th"] == "" and detail["body_en"] == ""


async def test_switching_source_clears_the_other_side(authed):
    await add_article(authed)
    await authed.post(
        "/admin/articles/1",
        data=article_data(authed, source="external", external_url="https://dev.to/x", platform="dev.to"),
    )
    assert (await public(authed, "/api/articles/1"))["body_en"] == ""
    await authed.post("/admin/articles/1", data=article_data(authed, external_url="https://dev.to/x", platform="dev.to"))
    detail = await public(authed, "/api/articles/1")
    assert detail["external_url"] == "" and detail["platform"] == "" and detail["body_en"] == "# Body"


async def test_only_published_articles_are_public_newest_first(authed):
    await add_article(authed, title_en="Old", published_on="2025-01-01")
    await add_article(authed, title_en="New", published_on="2026-06-01")
    await add_article(authed, title_en="Draft", status="draft")
    await add_article(authed, title_en="Hidden", status="hidden")
    items = (await public(authed, "/api/articles"))["items"]
    assert [i["title_en"] for i in items] == ["New", "Old"]
    assert (await authed.get("/api/articles/3")).status_code == 404
    assert (await authed.get("/api/articles/4")).status_code == 404


async def test_validation_errors_keep_the_form(authed):
    for override, message in (
        ({"title_th": "", "title_en": ""}, "ชื่อบทความ"),
        ({"source": "bogus"}, "ชนิดบทความไม่ถูกต้อง"),
        ({"status": "bogus"}, "สถานะไม่ถูกต้อง"),
        ({"published_on": "not-a-date"}, "วันที่ไม่ถูกต้อง"),
        ({"source": "external", "external_url": "ftp://x", "platform": "Medium"}, "http://"),
        ({"source": "external", "external_url": "https://x.com/a", "platform": ""}, "ชื่อแพลตฟอร์ม"),
        ({"body_th": "", "body_en": ""}, "ต้องมีเนื้อหา"),
    ):
        resp = await add_article(authed, **override)
        assert resp.status_code == 422 and message in resp.text, override
    assert (await public(authed, "/api/articles"))["total"] == 0


async def test_tags_trash_and_restore(authed):
    await add_tag(authed, "PostgreSQL", "pg")
    await add_article(authed, tag_ids=["1"], new_tags=["pg", "SQL"])
    names = [t["name"] for t in (await public(authed, "/api/articles/1"))["tags"]]
    assert names == ["PostgreSQL", "SQL"]
    await authed.post("/admin/articles/1/trash", data={"csrf_token": authed.csrf})
    assert (await public(authed, "/api/articles"))["total"] == 0
    assert "Why Postgres" in (await authed.get("/admin/articles?trash=true")).text
    await authed.post("/admin/articles/1/restore", data={"csrf_token": authed.csrf})
    assert (await public(authed, "/api/articles"))["total"] == 0  # back hidden until reviewed


async def test_untranslated_flag_form_pages_and_csrf(authed):
    await add_article(authed, summary_en="")
    assert "ยังไม่ได้แปล 1 ช่อง" in (await authed.get("/admin/articles")).text
    assert 'name="source"' in (await authed.get("/admin/articles/new")).text
    assert "Why Postgres" in (await authed.get("/admin/articles/1/edit")).text
    assert (await authed.post("/admin/articles", data={"title_en": "x"})).status_code == 403
