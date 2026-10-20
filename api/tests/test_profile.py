from .test_projects import add_category, add_project, public

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"\x00" * 32


async def post(c, path, **data):
    return await c.post(path, data={"csrf_token": c.csrf, **data})


async def send(c, path, name, data):
    return await c.post(path, data={"csrf_token": c.csrf}, files=[("file", (name, data, "application/octet-stream"))])


async def test_empty_profile_has_no_broken_urls(authed):
    body = await public(authed, "/api/profile")
    assert body["photo_url"] is None and body["cv_th_url"] is None and body["cv_en_url"] is None
    assert body["links"] == [] and body["name_en"] == ""


async def test_text_fields_save_and_show_publicly(authed):
    resp = await post(
        authed,
        "/admin/profile",
        name_th="อาร์ม",
        name_en="Arm",
        intro_th="สวัสดี",
        intro_en="Hello",
        location_th="กรุงเทพ",
        location_en="Bangkok",
        email="arm@example.com",
    )
    assert resp.status_code == 303
    body = await public(authed, "/api/profile")
    assert body["name_th"] == "อาร์ม" and body["intro_en"] == "Hello" and body["email"] == "arm@example.com"
    assert "Arm" in (await authed.get("/admin/profile")).text


async def test_bad_email_keeps_what_was_typed(authed):
    resp = await post(authed, "/admin/profile", name_en="Arm", email="not-an-email")
    assert resp.status_code == 422 and "อีเมลไม่ถูกต้อง" in resp.text and "not-an-email" in resp.text
    assert (await public(authed, "/api/profile"))["name_en"] == ""


async def test_untranslated_field_is_flagged(authed):
    await post(authed, "/admin/profile", name_th="อาร์ม", name_en="")
    assert "ยังไม่ได้กรอก" in (await authed.get("/admin/profile")).text


async def test_photo_upload_replace_and_remove(authed, storage):
    assert (await send(authed, "/admin/profile/photo", "me.png", PNG)).status_code == 303
    url = (await public(authed, "/api/profile"))["photo_url"]
    assert url.startswith("/api/profile/photo?v=")
    image = await authed.get(url)
    assert image.status_code == 200 and image.content == PNG and image.headers["content-type"] == "image/png"
    assert "immutable" in image.headers["cache-control"]
    first_keys = set(storage.files)
    await send(authed, "/admin/profile/photo", "me2.jpg", JPEG)
    new_url = (await public(authed, "/api/profile"))["photo_url"]
    assert new_url != url  # version tag changed
    assert len(storage.files) == 1 and not first_keys & set(storage.files)  # old file deleted
    assert (await authed.get("/admin/profile/photo")).status_code == 200
    await post(authed, "/admin/profile/photo/remove")
    assert (await public(authed, "/api/profile"))["photo_url"] is None
    assert not storage.files
    assert (await authed.get("/api/profile/photo")).status_code == 404


async def test_photo_must_really_be_an_image_and_not_too_large(authed, storage, monkeypatch):
    assert (await send(authed, "/admin/profile/photo", "me.png", b"<script>x</script>")).status_code == 415
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    assert (await send(authed, "/admin/profile/photo", "big.png", PNG + b"\x00" * (1024 * 1024))).status_code == 413
    assert not storage.files


async def test_cv_upload_per_language(authed, storage):
    assert (await send(authed, "/admin/profile/cv/th", "resume.pdf", PDF)).status_code == 303
    body = await public(authed, "/api/profile")
    assert body["cv_th_url"].startswith("/api/profile/cv/th?v=") and body["cv_en_url"] is None
    cv = await authed.get(body["cv_th_url"])
    assert cv.status_code == 200 and cv.content == PDF
    assert cv.headers["content-type"] == "application/pdf"
    assert 'filename="cv-th.pdf"' in cv.headers["content-disposition"]
    assert "resume.pdf" in (await authed.get("/admin/profile")).text
    assert (await authed.get("/api/profile/cv/en")).status_code == 404
    await post(authed, "/admin/profile/cv/th/remove")
    assert (await public(authed, "/api/profile"))["cv_th_url"] is None and not storage.files


async def test_cv_must_be_pdf_and_language_must_exist(authed):
    assert (await send(authed, "/admin/profile/cv/en", "cv.pdf", b"MZ not a pdf")).status_code == 415
    assert (await send(authed, "/admin/profile/cv/fr", "cv.pdf", PDF)).status_code == 404
    assert (await authed.get("/api/profile/cv/fr")).status_code == 404


async def test_contact_links_add_edit_order_trash_restore(authed):
    await post(authed, "/admin/profile/links", label="GitHub", url="https://github.com/arm")
    await post(authed, "/admin/profile/links", label="LinkedIn", url="https://linkedin.com/in/arm")
    await post(authed, "/admin/profile/links/1/move", direction="down")
    assert [link["label"] for link in (await public(authed, "/api/profile"))["links"]] == ["LinkedIn", "GitHub"]
    await post(authed, "/admin/profile/links/1", label="GH", url="https://github.com/arm2")
    links = (await public(authed, "/api/profile"))["links"]
    assert links[1] == {"id": 1, "label": "GH", "url": "https://github.com/arm2"}
    await post(authed, "/admin/profile/links/2/trash")
    assert [link["label"] for link in (await public(authed, "/api/profile"))["links"]] == ["GH"]
    assert "กู้คืน LinkedIn" in (await authed.get("/admin/profile")).text
    await post(authed, "/admin/profile/links/2/restore")
    assert len((await public(authed, "/api/profile"))["links"]) == 2


async def test_contact_link_validation(authed):
    for data, message in (
        ({"label": "", "url": "https://x.com"}, "ต้องกรอกชื่อช่องทาง"),
        ({"label": "X", "url": "javascript:alert(1)"}, "ลิงก์ต้องขึ้นต้นด้วย"),
    ):
        resp = await post(authed, "/admin/profile/links", **data)
        assert resp.status_code == 422 and message in resp.text
    assert (await public(authed, "/api/profile"))["links"] == []


async def test_profile_mutations_need_csrf_and_login(authed, client):
    assert (await authed.post("/admin/profile", data={"name_en": "x"})).status_code == 403
    assert (await authed.post("/admin/profile/photo", files=[("file", ("a.png", PNG, "image/png"))])).status_code == 403
    client.cookies.clear()
    assert (await client.get("/admin/profile")).status_code == 303
    assert (await client.get("/admin/profile/photo")).status_code == 303


async def test_settings_drive_default_page_sizes(authed):
    await add_category(authed)
    for n in range(3):
        await add_project(authed, title_en=f"P{n}", featured="on")
    assert (await public(authed, "/api/settings")) == {
        "featured_limit": 6,
        "projects_page_size": 12,
        "articles_page_size": 12,
        "how_i_work_project_id": None,
    }
    resp = await post(authed, "/admin/settings", featured_limit="2", projects_page_size="1", articles_page_size="5")
    assert resp.status_code == 303
    assert (await public(authed, "/api/settings"))["featured_limit"] == 2
    listing = await public(authed)
    assert listing["total"] == 3 and len(listing["items"]) == 1
    assert len(await public(authed, "/api/projects/featured")) == 2
    assert len((await public(authed, "/api/projects?limit=3"))["items"]) == 3  # explicit limit still wins


async def test_settings_validation(authed):
    for bad in ("0", "61", "abc", ""):
        resp = await post(authed, "/admin/settings", featured_limit=bad, projects_page_size="12", articles_page_size="12")
        assert resp.status_code == 422 and "ต้องเป็นตัวเลข 1–60" in resp.text
    assert (await public(authed, "/api/settings"))["featured_limit"] == 6
    assert (await authed.post("/admin/settings", data={"featured_limit": "3"})).status_code == 403
