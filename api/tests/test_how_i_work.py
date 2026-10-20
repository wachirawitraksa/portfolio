from .test_projects import add_category, add_project, public

SIZES = {"featured_limit": "6", "projects_page_size": "12", "articles_page_size": "12"}


async def choose(c, project_id):
    return await c.post(
        "/admin/settings", data={"csrf_token": c.csrf, **SIZES, "how_i_work_project_id": str(project_id)}
    )


async def test_nothing_is_chosen_by_default(authed):
    assert await public(authed, "/api/how-i-work") is None
    assert (await public(authed, "/api/settings"))["how_i_work_project_id"] is None


async def test_the_chosen_project_is_returned_in_full(authed):
    await add_category(authed)
    await add_project(authed, title_en="Plain one")
    await add_project(authed, title_en="The story", work_en="How I built it", result_en="It worked")
    assert (await choose(authed, 2)).status_code == 303
    story = await public(authed, "/api/how-i-work")
    assert story["id"] == 2 and story["title_en"] == "The story"
    assert story["work_en"] == "How I built it" and story["result_en"] == "It worked" and story["images"] == []
    assert (await public(authed, "/api/settings"))["how_i_work_project_id"] == 2
    assert story == await public(authed, "/api/projects/2")  # same shape as the detail endpoint


async def test_the_form_shows_the_current_choice_and_can_clear_it(authed):
    await add_category(authed)
    await add_project(authed, title_en="The story", title_th="เรื่องเล่า")
    await choose(authed, 1)
    page = (await authed.get("/admin/settings")).text
    assert '<option value="1" selected>' in page and "เรื่องเล่า" in page
    await authed.post("/admin/settings", data={"csrf_token": authed.csrf, **SIZES, "how_i_work_project_id": ""})
    assert await public(authed, "/api/how-i-work") is None
    assert "selected" not in (await authed.get("/admin/settings")).text.split("how_i_work_project_id")[1].split("</select>")[0]


async def test_an_unpublished_choice_stays_off_the_public_site(authed):
    await add_category(authed)
    await add_project(authed, title_en="Draft story", status="draft")
    await choose(authed, 1)
    assert "(ยังไม่เผยแพร่)" in (await authed.get("/admin/settings")).text  # the owner is told
    assert await public(authed, "/api/how-i-work") is None
    await authed.post("/admin/projects/1", data={"csrf_token": authed.csrf, "title_en": "Draft story", "status": "published"})
    assert (await public(authed, "/api/how-i-work"))["title_en"] == "Draft story"


async def test_a_trashed_choice_disappears_without_breaking_anything(authed):
    await add_category(authed)
    await add_project(authed, title_en="Soon gone")
    await choose(authed, 1)
    await authed.post("/admin/projects/1/trash", data={"csrf_token": authed.csrf})
    assert await public(authed, "/api/how-i-work") is None
    assert (await authed.get("/admin/settings")).status_code == 200


async def test_bad_choices_are_refused_and_nothing_else_is_saved(authed):
    await add_category(authed)
    await add_project(authed, title_en="Trashed")
    await authed.post("/admin/projects/1/trash", data={"csrf_token": authed.csrf})
    for bad in ("999", "abc", "1"):  # unknown, not a number, trashed
        resp = await authed.post(
            "/admin/settings",
            data={"csrf_token": authed.csrf, "featured_limit": "3", "projects_page_size": "9", "articles_page_size": "9", "how_i_work_project_id": bad},
        )
        assert resp.status_code == 422 and "วิธีการทำงาน" in resp.text, bad
    assert (await public(authed, "/api/settings"))["featured_limit"] == 6  # the other fields were not half-saved
