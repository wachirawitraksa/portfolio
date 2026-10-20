async def add_category(c, th="แอป", en="Apps"):
    await c.post("/admin/categories", data={"name_th": th, "name_en": en, "csrf_token": c.csrf})


async def add_tag(c, name, aliases=""):
    return await c.post("/admin/tags", data={"name": name, "aliases": aliases, "csrf_token": c.csrf})


def project_data(c, **overrides):
    data = {
        "title_th": "ระบบสต็อก",
        "title_en": "Stock system",
        "problem_th": "นับของด้วยมือ",
        "problem_en": "Counting by hand",
        "status": "published",
        "category_ids": ["1"],
        "csrf_token": c.csrf,
    }
    data.update(overrides)
    return data


async def add_project(c, **overrides):
    return await c.post("/admin/projects", data=project_data(c, **overrides))


async def public(c, path="/api/projects"):
    return (await c.get(path)).json()


async def titles(c, query=""):
    return [p["title_en"] for p in (await public(c, f"/api/projects{query}"))["items"]]


async def test_mutations_without_csrf_are_refused(authed):
    assert (await authed.post("/admin/projects", data={"title_th": "x"})).status_code == 403
    assert (await authed.post("/admin/tags", data={"name": "x"})).status_code == 403


async def test_create_project_shows_in_admin_and_public_api(authed):
    await add_category(authed)
    resp = await add_project(authed, year="2025", repo_url="https://github.com/me/stock")
    assert resp.status_code == 303
    assert "ระบบสต็อก" in (await authed.get("/admin/projects")).text
    body = await public(authed)
    assert body["total"] == 1
    item = body["items"][0]
    assert item["title_en"] == "Stock system" and item["year"] == 2025
    assert item["categories"] == [{"id": 1, "name_th": "แอป", "name_en": "Apps"}]


async def test_only_published_projects_are_public(authed):
    await add_category(authed)
    await add_project(authed, title_en="Draft one", status="draft")
    await add_project(authed, title_en="Hidden one", status="hidden")
    await add_project(authed, title_en="Live one")
    assert await titles(authed) == ["Live one"]
    assert (await authed.get("/api/projects/1")).status_code == 404
    assert (await authed.get("/api/projects/3")).status_code == 200


async def test_validation_errors_keep_what_was_typed(authed):
    await add_category(authed)
    resp = await add_project(authed, title_th="", title_en="")
    assert resp.status_code == 422 and "ต้องกรอกชื่อ" in resp.text
    resp = await add_project(authed, title_th="เก็บไว้ในฟอร์ม", year="abc")
    assert resp.status_code == 422 and "เก็บไว้ในฟอร์ม" in resp.text
    resp = await add_project(authed, repo_url="javascript:alert(1)")
    assert resp.status_code == 422
    assert (await public(authed))["total"] == 0


async def test_at_most_three_categories(authed):
    for n in range(4):
        await add_category(authed, f"ก{n}", f"C{n}")
    assert (await add_project(authed, category_ids=["1", "2", "3", "4"])).status_code == 422
    assert (await add_project(authed, category_ids=["1", "2", "3"])).status_code == 303


async def test_untranslated_fields_are_flagged_but_still_public(authed):
    await add_category(authed)
    await add_project(authed, title_en="", problem_en="")
    assert "ยังไม่ได้แปล 2 ช่อง" in (await authed.get("/admin/projects")).text
    item = (await public(authed))["items"][0]
    assert item["title_th"] == "ระบบสต็อก" and item["title_en"] == ""


async def test_edit_replaces_fields_categories_and_tags(authed):
    await add_category(authed, "ก", "A")
    await add_category(authed, "ข", "B")
    await add_tag(authed, "Python")
    await add_project(authed, category_ids=["1"], tag_ids=["1"])
    await authed.post("/admin/projects/1", data=project_data(authed, title_en="Renamed", category_ids=["2"]))
    item = (await public(authed))["items"][0]
    assert item["title_en"] == "Renamed"
    assert [c["name_en"] for c in item["categories"]] == ["B"]
    assert item["tags"] == []


async def test_search_matches_text_aliases_and_tags(authed):
    await add_category(authed)
    await add_tag(authed, "PostgreSQL", "pg\npostgres")
    await add_project(authed, title_en="Alpha", problem_en="needs a database", tag_ids=["1"])
    await add_project(authed, title_en="Beta", aliases="Project Moonlight")
    assert await titles(authed, "?q=database") == ["Alpha"]
    assert await titles(authed, "?q=MOONLIGHT") == ["Beta"]
    assert await titles(authed, "?q=pg") == ["Alpha"]
    assert await titles(authed, "?q=ระบบสต็อก") == ["Alpha", "Beta"]
    assert await titles(authed, "?q=nothing-matches") == []
    assert await titles(authed, "?q=%25") == []  # a literal %, not a wildcard


async def test_filter_by_tag_and_category(authed):
    await add_category(authed, "ก", "A")
    await add_category(authed, "ข", "B")
    await add_tag(authed, "Python")
    await add_tag(authed, "Docker")
    await add_project(authed, title_en="One", category_ids=["1"], tag_ids=["1", "2"])
    await add_project(authed, title_en="Two", category_ids=["2"], tag_ids=["1"])
    assert await titles(authed, "?tag=1") == ["One", "Two"]
    assert await titles(authed, "?tag=1&tag=2") == ["One"]  # every tag must match
    assert await titles(authed, "?category=2") == ["Two"]
    assert [t["name"] for t in await public(authed, "/api/tags")] == ["Docker", "Python"]


async def test_sort_and_paging_with_many_projects(authed):
    await add_category(authed)
    for n in range(1, 8):
        await add_project(authed, title_en=f"P{n}", year=str(2020 + n % 3))
    page = await public(authed, "/api/projects?limit=3&offset=3")
    assert page["total"] == 7 and [p["title_en"] for p in page["items"]] == ["P4", "P5", "P6"]
    # P2 and P5 share the newest year (2022); the later one comes first.
    assert (await titles(authed, "?sort=newest&limit=2")) == ["P5", "P2"]
    assert (await authed.get("/api/projects?limit=1000")).status_code == 422


async def test_reorder_and_featured(authed):
    await add_category(authed)
    for n in "ABC":
        await add_project(authed, title_en=n)
    await authed.post("/admin/projects/3/move", data={"direction": "up", "csrf_token": authed.csrf})
    assert await titles(authed) == ["A", "C", "B"]
    assert await public(authed, "/api/projects/featured") == []
    await authed.post("/admin/projects/2/feature", data={"csrf_token": authed.csrf})
    await authed.post("/admin/projects/3/feature", data={"csrf_token": authed.csrf})
    featured = await public(authed, "/api/projects/featured")
    assert [p["title_en"] for p in featured] == ["C", "B"]
    assert len(await public(authed, "/api/projects/featured?limit=1")) == 1


async def test_trash_and_restore(authed):
    await add_category(authed)
    await add_project(authed)
    await authed.post("/admin/projects/1/trash", data={"csrf_token": authed.csrf})
    assert (await public(authed))["total"] == 0
    assert "ระบบสต็อก" not in (await authed.get("/admin/projects")).text
    assert "ระบบสต็อก" in (await authed.get("/admin/projects?trash=true")).text
    await authed.post("/admin/projects/1/restore", data={"csrf_token": authed.csrf})
    assert "ระบบสต็อก" in (await authed.get("/admin/projects")).text
    assert (await public(authed))["total"] == 0  # comes back hidden


async def test_category_in_use_cannot_be_trashed(authed):
    await add_category(authed)
    await add_project(authed)
    resp = await authed.post("/admin/categories/1/trash", data={"csrf_token": authed.csrf})
    assert resp.status_code == 409 and "ซ่อน" in resp.text
    # Once the project is in the trash, the category is free to go.
    await authed.post("/admin/projects/1/trash", data={"csrf_token": authed.csrf})
    resp = await authed.post("/admin/categories/1/trash", data={"csrf_token": authed.csrf})
    assert resp.status_code == 303


async def test_tags_crud_and_trash(authed):
    assert (await add_tag(authed, "  ")).status_code == 422
    await add_tag(authed, "PostgreSQL", "pg, postgres, PG")
    page = (await authed.get("/admin/tags")).text
    assert "PostgreSQL" in page and "pg, postgres" in page  # repeats removed
    await authed.post("/admin/tags/1/trash", data={"csrf_token": authed.csrf})
    assert "PostgreSQL" not in (await authed.get("/admin/tags")).text
    await authed.post("/admin/tags/1/restore", data={"csrf_token": authed.csrf})
    assert "PostgreSQL" in (await authed.get("/admin/tags")).text


async def add_kind(c, th, en=""):
    return await c.post("/admin/kinds", data={"name_th": th, "name_en": en, "csrf_token": c.csrf})


async def test_new_tags_and_categories_are_created_from_the_card(authed):
    await add_tag(authed, "PostgreSQL", "pg")
    resp = await add_project(
        authed, category_ids=[], new_categories=["ใบเซอร์", "Awards"], new_tags=["pg", "Rust", "rust"]
    )
    assert resp.status_code == 303
    item = (await public(authed))["items"][0]
    # "pg" is an alias of the existing tag, so it is picked, not duplicated; "rust" repeats once.
    assert sorted(t["name"] for t in item["tags"]) == ["PostgreSQL", "Rust"]
    assert sorted((c["name_th"], c["name_en"]) for c in item["categories"]) == [("", "Awards"), ("ใบเซอร์", "")]
    # Typing a name that already exists reuses it.
    await add_project(authed, category_ids=[], new_categories=["awards"], new_tags=["RUST"])
    assert len((await public(authed, "/api/tags"))) == 2
    assert "Awards" in (await authed.get("/admin/categories")).text


async def test_new_names_count_toward_the_three_category_limit(authed):
    await add_category(authed, "ก", "A")
    resp = await add_project(authed, category_ids=["1"], new_categories=["x", "y", "z"])
    assert resp.status_code == 422
    assert "x" in resp.text  # typed names stay on the card
    assert (await authed.get("/admin/categories")).text.count("<tr>") == 2  # header + the one existing


async def test_kinds_certificate_fields_and_filter(authed):
    await add_kind(authed, "ผลงาน", "Project")
    await add_kind(authed, "ใบเซอร์", "Certificate")
    await add_project(authed, title_en="App", kind_id="1")
    resp = await add_project(
        authed,
        title_en="AWS cert",
        kind_id="2",
        issuer="Amazon",
        issued_on="2025-03-14",
        verify_url="https://example.com/verify/1",
    )
    assert resp.status_code == 303
    assert await titles(authed, "?kind=2") == ["AWS cert"]
    cert = (await public(authed, "/api/projects/2"))
    assert cert["issuer"] == "Amazon" and cert["issued_on"] == "2025-03-14"
    assert cert["kind"]["name_en"] == "Certificate"
    assert [k["name_en"] for k in await public(authed, "/api/kinds")] == ["Project", "Certificate"]
    assert (await add_project(authed, kind_id="99")).status_code == 422
    assert (await add_project(authed, issued_on="14/03/2025")).status_code == 422
    assert (await add_project(authed, verify_url="javascript:x")).status_code == 422


async def test_kind_in_use_cannot_be_trashed(authed):
    await add_kind(authed, "ผลงาน", "Project")
    await add_project(authed, kind_id="1", category_ids=[])
    resp = await authed.post("/admin/kinds/1/trash", data={"csrf_token": authed.csrf})
    assert resp.status_code == 409
    await authed.post("/admin/projects/1/trash", data={"csrf_token": authed.csrf})
    assert (await authed.post("/admin/kinds/1/trash", data={"csrf_token": authed.csrf})).status_code == 303


async def test_form_lists_each_category_and_tag_once(authed):
    await add_category(authed, "กาท", "adas")
    await add_tag(authed, "PostgreSQL", "pg, postgres")
    page = (await authed.get("/admin/projects/new")).text
    assert page.count('<option value="กาท"') == 1  # the English name is not a second entry
    assert 'value="adas"' not in page
    assert page.count('<option value="PostgreSQL"') == 1
    assert 'value="pg"' not in page
    # Typing the English name or an alias still picks the existing item, not a duplicate.
    await add_project(authed, category_ids=[], new_categories=["ADAS"], new_tags=["PG"])
    item = (await public(authed))["items"][0]
    assert [c["name_th"] for c in item["categories"]] == ["กาท"] and [t["name"] for t in item["tags"]] == ["PostgreSQL"]
    assert len(await public(authed, "/api/categories")) == 1
