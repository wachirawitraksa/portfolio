async def create(client, th, en):
    return await client.post(
        "/admin/categories", data={"name_th": th, "name_en": en, "csrf_token": client.csrf}
    )


async def public_names(client):
    return [c["name_en"] for c in (await client.get("/api/categories")).json()]


async def test_mutations_without_csrf_are_refused(authed):
    resp = await authed.post("/admin/categories", data={"name_th": "x", "name_en": "x"})
    assert resp.status_code == 403
    resp = await authed.post("/admin/categories", data={"name_th": "x", "csrf_token": "forged"})
    assert resp.status_code == 403


async def test_create_edit_and_list_in_both_languages(authed):
    assert (await create(authed, "แอปที่เปิดใช้ได้", "Live apps")).status_code == 303
    page = (await authed.get("/admin/categories")).text
    assert "แอปที่เปิดใช้ได้" in page and "Live apps" in page

    await authed.post("/admin/categories/1", data={"name_th": "แอป", "name_en": "Apps", "csrf_token": authed.csrf})
    assert await public_names(authed) == ["Apps"]


async def test_missing_translation_is_flagged_in_the_list(authed):
    await create(authed, "ทดลอง", "")
    assert "ยังไม่ได้กรอก" in (await authed.get("/admin/categories")).text


async def test_hidden_categories_leave_the_public_api(authed):
    await create(authed, "ก", "A")
    await create(authed, "ข", "B")
    await authed.post("/admin/categories/1/hide", data={"csrf_token": authed.csrf})
    assert await public_names(authed) == ["B"]
    await authed.post("/admin/categories/1/hide", data={"csrf_token": authed.csrf})
    assert await public_names(authed) == ["A", "B"]


async def test_reorder(authed):
    for th, en in (("ก", "A"), ("ข", "B"), ("ค", "C")):
        await create(authed, th, en)
    await authed.post("/admin/categories/3/move", data={"direction": "up", "csrf_token": authed.csrf})
    assert await public_names(authed) == ["A", "C", "B"]
    await authed.post("/admin/categories/1/move", data={"direction": "up", "csrf_token": authed.csrf})
    assert await public_names(authed) == ["A", "C", "B"]  # already first: no change


async def test_trash_and_restore(authed):
    await create(authed, "งานทดลองพิเศษ", "Special")
    await authed.post("/admin/categories/1/trash", data={"csrf_token": authed.csrf})
    assert await public_names(authed) == []
    assert "งานทดลองพิเศษ" not in (await authed.get("/admin/categories")).text
    assert "งานทดลองพิเศษ" in (await authed.get("/admin/categories?trash=true")).text

    await authed.post("/admin/categories/1/restore", data={"csrf_token": authed.csrf})
    assert "งานทดลองพิเศษ" in (await authed.get("/admin/categories")).text
    # Restored items come back hidden until they are reviewed.
    assert await public_names(authed) == []
