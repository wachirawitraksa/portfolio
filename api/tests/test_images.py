from .test_projects import add_category, add_project, public

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 16


async def upload(c, project_id=1, *files):
    parts = [("files", (name, data, "application/octet-stream")) for name, data in files]
    return await c.post(f"/admin/projects/{project_id}/images", data={"csrf_token": c.csrf}, files=parts)


async def act(c, path, **data):
    return await c.post(f"/admin/projects/1/images/{path}", data={"csrf_token": c.csrf, **data})


async def setup(c, **overrides):
    await add_category(c)
    await add_project(c, **overrides)


async def test_upload_needs_csrf(authed):
    await setup(authed)
    resp = await authed.post("/admin/projects/1/images", files=[("files", ("a.png", PNG, "image/png"))])
    assert resp.status_code == 403


async def test_first_image_becomes_cover_and_is_public(authed, storage):
    await setup(authed)
    assert (await upload(authed, 1, ("a.png", PNG), ("b.jpg", JPEG))).status_code == 303
    assert len(storage.files) == 2
    detail = await public(authed, "/api/projects/1")
    assert [i["is_cover"] for i in detail["images"]] == [True, False]
    assert detail["cover_url"] == detail["images"][0]["url"]
    image = await authed.get(detail["images"][0]["url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.headers["x-content-type-options"] == "nosniff"
    assert image.content == PNG
    card = (await public(authed))["items"][0]
    assert card["cover_url"] == detail["cover_url"] and "images" not in card


async def test_type_comes_from_the_bytes_not_the_name(authed, storage):
    await setup(authed)
    resp = await upload(authed, 1, ("fake.png", b"<script>alert(1)</script>"))
    assert resp.status_code == 415
    assert not storage.files
    assert (await upload(authed, 1, ("photo.dat", WEBP))).status_code == 303
    assert list(storage.files.values())[0][1] == "image/webp"


async def test_too_large_is_refused(authed, storage, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    await setup(authed)
    resp = await upload(authed, 1, ("big.png", PNG + b"\x00" * (1024 * 1024)))
    assert resp.status_code == 413
    assert not storage.files


async def test_unknown_project_is_404(authed):
    assert (await upload(authed, 99, ("a.png", PNG))).status_code == 404


async def test_draft_images_are_not_public_but_admin_can_preview(authed):
    await setup(authed, status="draft")
    await upload(authed, 1, ("a.png", PNG))
    assert (await authed.get("/api/media/1")).status_code == 404
    assert (await authed.get("/admin/media/1")).status_code == 200


async def test_admin_preview_needs_login(client):
    assert (await client.get("/admin/media/1")).status_code == 303


async def test_cover_caption_and_order(authed):
    await setup(authed)
    await upload(authed, 1, ("a.png", PNG), ("b.png", PNG))
    await act(authed, "2/cover")
    await act(authed, "2/caption", caption_th="หน้าจอหลัก", caption_en="Main screen")
    await act(authed, "2/move", direction="up")
    images = (await public(authed, "/api/projects/1"))["images"]
    assert [i["id"] for i in images] == [2, 1]
    assert [i["is_cover"] for i in images] == [True, False]
    assert images[0]["caption_th"] == "หน้าจอหลัก" and images[0]["caption_en"] == "Main screen"


async def test_trash_moves_cover_and_restore_brings_image_back(authed):
    await setup(authed)
    await upload(authed, 1, ("a.png", PNG), ("b.png", PNG))
    await act(authed, "1/trash")
    images = (await public(authed, "/api/projects/1"))["images"]
    assert [(i["id"], i["is_cover"]) for i in images] == [(2, True)]
    assert (await authed.get("/api/media/1")).status_code == 404
    assert "กู้คืนรูป #1" in (await authed.get("/admin/projects/1/edit")).text
    await act(authed, "1/restore")
    assert [i["id"] for i in (await public(authed, "/api/projects/1"))["images"]] == [1, 2]


async def test_images_of_another_project_are_untouchable(authed):
    await setup(authed)
    await add_project(authed, title_en="Other")
    await upload(authed, 2, ("a.png", PNG))
    assert (await act(authed, "1/trash")).status_code == 404


async def test_edit_page_shows_upload_form_only_for_saved_projects(authed):
    await setup(authed)
    assert "บันทึกรายการก่อน" in (await authed.get("/admin/projects/new")).text
    assert 'enctype="multipart/form-data"' in (await authed.get("/admin/projects/1/edit")).text
