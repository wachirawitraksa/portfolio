"""Headline, tag groups, site title, hidden kinds, recent updates, smaller images and draft previews."""
import io
import re
import time

from PIL import Image
from sqlalchemy import select, update

from app import previews
from app.db import SessionLocal
from app.models import Project, User, WorkEntry
from app.rag.index import collect

from .test_articles import add_article
from .test_education import add_edu
from .test_images import upload
from .test_kind_fields import add_kind
from .test_projects import add_category, add_project, add_tag, public, titles
from .test_work import add_work


async def post(c, path, **data):
    return await c.post(path, data={"csrf_token": c.csrf, **data})


def picture(width=1200, height=600, kind="PNG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (30, 90, 160)).save(out, kind)
    return out.getvalue()


# --- hiding a kind -------------------------------------------------------------------------------------------


async def test_hiding_a_kind_hides_what_is_filed_under_it(authed):
    await add_category(authed)
    await add_kind(authed, "Project")
    await add_kind(authed, "Award")
    await add_project(authed, title_en="App", kind_id="1", featured="on")
    await add_project(authed, title_en="Prize", kind_id="2", featured="on")
    await add_project(authed, title_en="Loose")  # no kind at all
    assert sorted(await titles(authed)) == ["App", "Loose", "Prize"]

    await post(authed, "/admin/kinds/2/hide")
    assert sorted(await titles(authed)) == ["App", "Loose"]
    assert (await authed.get("/api/projects/2")).status_code == 404
    assert [p["title_en"] for p in await public(authed, "/api/projects/featured")] == ["App"]
    assert [t["name"] for t in await public(authed, "/api/tags")] == []

    await post(authed, "/admin/kinds/2/hide")  # shown again
    assert sorted(await titles(authed)) == ["App", "Loose", "Prize"]


async def test_the_question_box_does_not_read_a_hidden_kind(authed):
    await add_category(authed)
    await add_kind(authed, "Award")
    await add_project(authed, title_en="Prize", kind_id="1")
    async with SessionLocal() as db:
        assert {c.source_id for c in await collect(db) if c.source_type == "project"} == {1}
    await post(authed, "/admin/kinds/1/hide")
    async with SessionLocal() as db:
        assert not [c for c in await collect(db) if c.source_type == "project"]


async def test_a_hidden_kinds_pictures_do_not_leak(authed):
    await add_category(authed)
    await add_kind(authed, "Award")
    await add_project(authed, title_en="Prize", kind_id="1")
    await upload(authed, 1, ("a.png", picture(40, 20)))
    assert (await authed.get("/api/media/1")).status_code == 200
    await post(authed, "/admin/kinds/1/hide")
    assert (await authed.get("/api/media/1")).status_code == 404


# --- headline, tag group, site title --------------------------------------------------------------------------


async def test_headline_is_saved_and_public(authed):
    assert (await public(authed, "/api/profile"))["headline_en"] == ""
    resp = await post(authed, "/admin/profile", name_en="Jane", headline_th="วิศวกรซอฟต์แวร์", headline_en="Software Engineer")
    assert resp.status_code == 303
    profile = await public(authed, "/api/profile")
    assert (profile["headline_th"], profile["headline_en"]) == ("วิศวกรซอฟต์แวร์", "Software Engineer")
    assert "Software Engineer" in (await authed.get("/admin/profile")).text


async def test_a_headline_in_one_language_is_flagged(authed):
    await post(authed, "/admin/profile", headline_en="Software Engineer")
    page = (await authed.get("/admin/profile")).text
    flag = r'[^<]*<span class="[^"]*text-warning[^"]*">'  # the "not filled in" note
    assert re.search(r'for="headline_th">' + flag, page)  # the Thai half is flagged
    assert not re.search(r'for="headline_en">' + flag, page)


async def test_tag_group_is_saved_and_public(authed):
    await add_category(authed)
    await post(authed, "/admin/tags", name="React", aliases="", group_th="ฟรอนต์เอนด์", group_en="Frontend")
    await post(authed, "/admin/tags", name="Postgres")
    await add_project(authed, title_en="App", tag_ids=["1", "2"])
    tags = {t["name"]: t for t in await public(authed, "/api/tags")}
    assert (tags["React"]["group_th"], tags["React"]["group_en"]) == ("ฟรอนต์เอนด์", "Frontend")
    assert (tags["Postgres"]["group_th"], tags["Postgres"]["group_en"]) == ("", "")
    await post(authed, "/admin/tags/1", name="React", aliases="", group_th="", group_en="UI")
    assert [t["group_en"] for t in await public(authed, "/api/tags") if t["name"] == "React"] == ["UI"]


async def test_site_title_and_description_are_saved_and_public(authed):
    s = await public(authed, "/api/settings")
    assert s["site_title_en"] == "" and s["site_description_th"] == ""
    resp = await post(
        authed, "/admin/settings", featured_limit="6", projects_page_size="12", articles_page_size="12",
        site_title_en="Jane Doe — Engineer", site_title_th="เจน", site_description_en="Things I built", site_description_th="สิ่งที่ผมทำ",
    )
    assert resp.status_code == 303
    s = await public(authed, "/api/settings")
    assert (s["site_title_en"], s["site_title_th"]) == ("Jane Doe — Engineer", "เจน")
    assert (s["site_description_en"], s["site_description_th"]) == ("Things I built", "สิ่งที่ผมทำ")


async def test_site_title_is_cut_to_its_limit(authed):
    await post(authed, "/admin/settings", featured_limit="6", projects_page_size="12", articles_page_size="12", site_title_en="x" * 500)
    assert len((await public(authed, "/api/settings"))["site_title_en"]) == 120


# --- recent updates ------------------------------------------------------------------------------------------


async def test_updates_list_what_was_edited_newest_first(authed):
    assert await public(authed, "/api/updates") == []
    await add_category(authed)
    await add_project(authed, title_en="First")
    await add_work(authed, position_en="Developer")
    await add_edu(authed, institution_en="Uni")
    await add_article(authed, title_en="Post")
    await post(authed, "/admin/profile", name_en="Jane")
    items = await public(authed, "/api/updates")
    assert {(i["type"], i["title_en"]) for i in items} == {
        ("project", "First"), ("work", "Developer"), ("education", "Uni"), ("article", "Post"), ("profile", "Jane"),
    }
    assert [i["at"] for i in items] == sorted((i["at"] for i in items), reverse=True)
    assert len(await public(authed, "/api/updates?limit=2")) == 2


async def test_an_edit_moves_an_entry_to_the_top(authed):
    await add_category(authed)
    await add_project(authed, title_en="Old")
    await add_project(authed, title_en="Newer")
    assert (await public(authed, "/api/updates"))[0]["title_en"] == "Newer"
    await post(authed, "/admin/projects/1", title_th="ระบบสต็อก", title_en="Old, edited", problem_th="x", problem_en="y", status="published", category_ids=["1"])
    assert (await public(authed, "/api/updates"))[0]["title_en"] == "Old, edited"


async def test_updates_leave_out_what_the_public_cannot_see(authed):
    await add_category(authed)
    await add_project(authed, title_en="Draft", status="draft")
    await add_project(authed, title_en="Live")
    await add_work(authed, position_en="Secret job")
    await post(authed, "/admin/work/1/hide")
    await add_article(authed, title_en="Unfinished", status="draft")
    assert [i["title_en"] for i in await public(authed, "/api/updates")] == ["Live"]


async def test_entries_from_before_the_stamp_existed_are_not_given_a_date(authed):
    await add_category(authed)
    await add_project(authed, title_en="Old one")
    async with SessionLocal() as db:  # what migration 0013 leaves behind: NULL, not "today"
        await db.execute(update(Project).values(updated_at=None))
        await db.commit()
    assert await public(authed, "/api/updates") == []


async def test_an_empty_profile_is_not_an_update(authed):
    await public(authed, "/api/profile")  # creates the empty row
    assert await public(authed, "/api/updates") == []


async def test_updates_limit_is_checked(authed):
    assert (await authed.get("/api/updates?limit=0")).status_code == 422
    assert (await authed.get("/api/updates?limit=31")).status_code == 422


# --- smaller pictures ----------------------------------------------------------------------------------------


async def test_a_width_gives_a_smaller_webp_and_keeps_the_original(authed, storage):
    await add_category(authed)
    await add_project(authed)
    await upload(authed, 1, ("big.png", picture(1200, 600)))
    resp = await authed.get("/api/media/1?w=480")
    assert resp.status_code == 200 and resp.headers["content-type"] == "image/webp"
    small = Image.open(io.BytesIO(resp.content))
    assert small.size == (480, 240)
    assert len(resp.content) < len(picture(1200, 600))
    assert any(k.startswith("thumbs/") and k.endswith("@480.webp") for k in storage.files)
    assert (await authed.get("/api/media/1")).headers["content-type"] == "image/png"  # the original is untouched


async def test_a_copy_is_made_once(authed, storage):
    await add_category(authed)
    await add_project(authed)
    await upload(authed, 1, ("big.png", picture(1200, 600)))
    first = await authed.get("/api/media/1?w=320")
    stored = {k: v for k, v in storage.files.items() if k.startswith("thumbs/")}
    assert len(stored) == 1
    original_key = next(k for k in storage.files if k.startswith("projects/"))
    del storage.files[original_key]  # the copy no longer needs the original
    assert (await authed.get("/api/media/1?w=320")).content == first.content


async def test_a_picture_already_narrower_is_served_as_it_is(authed, storage):
    await add_category(authed)
    await add_project(authed)
    small = picture(200, 100)
    await upload(authed, 1, ("small.png", small))
    resp = await authed.get("/api/media/1?w=480")
    assert resp.content == small and resp.headers["content-type"] == "image/png"
    assert not [k for k in storage.files if k.startswith("thumbs/")]


async def test_only_the_listed_widths_are_served(authed):
    await add_category(authed)
    await add_project(authed)
    await upload(authed, 1, ("big.png", picture(1200, 600)))
    for bad in ("0", "100", "481", "99999", "abc"):
        assert (await authed.get(f"/api/media/1?w={bad}")).status_code == 422, bad


async def test_a_file_pillow_cannot_read_is_served_as_it_is(authed):
    await add_category(authed)
    await add_project(authed)
    broken = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    await upload(authed, 1, ("broken.png", broken))
    resp = await authed.get("/api/media/1?w=320")
    assert resp.status_code == 200 and resp.content == broken


async def test_the_profile_photo_comes_in_widths_too(authed):
    await authed.post("/admin/profile/photo", data={"csrf_token": authed.csrf}, files=[("file", ("me.png", picture(1000, 1000), "image/png"))])
    resp = await authed.get("/api/profile/photo?w=320")
    assert resp.headers["content-type"] == "image/webp" and Image.open(io.BytesIO(resp.content)).size == (320, 320)
    assert (await authed.get("/api/profile/photo")).headers["content-type"] == "image/png"


async def test_a_draft_image_is_not_resizable_without_a_preview(authed):
    await add_category(authed)
    await add_project(authed, status="draft")
    await upload(authed, 1, ("big.png", picture(1200, 600)))
    assert (await authed.get("/api/media/1?w=320")).status_code == 404


# --- previews ------------------------------------------------------------------------------------------------


def token_of(location: str) -> str:
    return re.search(r"preview=([^&]+)", location).group(1)


async def test_the_admin_preview_link_goes_to_the_site_with_a_token(authed):
    await add_category(authed)
    await add_project(authed, status="draft")
    host = {"host": "admin.example.com"}
    resp = await authed.get("/admin/projects/1/preview", headers=host)
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("http://example.com/th/projects/1?preview=")
    authed.cookies.set("lang", "en")
    assert (await authed.get("/admin/projects/1/preview", headers=host)).headers["location"].startswith("http://example.com/en/projects/1?")


async def test_a_draft_can_be_read_with_its_token_only(authed):
    await add_category(authed)
    await add_project(authed, title_en="Draft", status="draft")
    assert (await authed.get("/api/projects/1")).status_code == 404
    token = token_of((await authed.get("/admin/projects/1/preview")).headers["location"])
    resp = await authed.get(f"/api/preview/projects/1?token={token}")
    assert resp.status_code == 200 and resp.json()["title_en"] == "Draft"
    assert resp.headers["cache-control"] == "no-store" and resp.headers["x-robots-tag"] == "noindex"
    assert (await authed.get("/api/preview/projects/1?token=nope")).status_code == 404
    assert (await authed.get("/api/preview/projects/1")).status_code == 422  # the token is required


async def test_a_token_is_for_one_entry(authed):
    await add_category(authed)
    await add_project(authed, title_en="One", status="draft")
    await add_project(authed, title_en="Two", status="draft")
    token = token_of((await authed.get("/admin/projects/1/preview")).headers["location"])
    assert (await authed.get(f"/api/preview/projects/2?token={token}")).status_code == 404
    await add_article(authed, status="draft")
    assert (await authed.get(f"/api/preview/articles/1?token={token}")).status_code == 404  # nor for another kind


async def test_a_token_expires_and_cannot_be_forged(authed):
    await add_category(authed)
    await add_project(authed, status="draft")
    async with SessionLocal() as db:
        old = await previews.mint(db, "project", 1, now=time.time() - previews.LIFETIME - 5)
        fresh = await previews.mint(db, "project", 1)
    assert (await authed.get(f"/api/preview/projects/1?token={old}")).status_code == 404
    assert (await authed.get(f"/api/preview/projects/1?token={fresh}")).status_code == 200
    body, signature = fresh.split(".")
    assert (await authed.get(f"/api/preview/projects/1?token={body}.{signature[::-1]}")).status_code == 404
    assert (await authed.get(f"/api/preview/projects/1?token={body}")).status_code == 404


async def test_changing_the_password_ends_every_preview_link(authed):
    await add_category(authed)
    await add_project(authed, status="draft")
    token = token_of((await authed.get("/admin/projects/1/preview")).headers["location"])
    assert (await authed.get(f"/api/preview/projects/1?token={token}")).status_code == 200
    async with SessionLocal() as db:
        await db.execute(update(User).values(password_hash="another-hash"))
        await db.commit()
    assert (await authed.get(f"/api/preview/projects/1?token={token}")).status_code == 404


async def test_a_trashed_entry_has_no_preview(authed):
    await add_category(authed)
    await add_project(authed, status="draft")
    token = token_of((await authed.get("/admin/projects/1/preview")).headers["location"])
    await post(authed, "/admin/projects/1/trash")
    assert (await authed.get(f"/api/preview/projects/1?token={token}")).status_code == 404


async def test_a_draft_images_load_with_the_preview_token(authed):
    await add_category(authed)
    await add_project(authed, status="draft")
    await upload(authed, 1, ("big.png", picture(1200, 600)))
    token = token_of((await authed.get("/admin/projects/1/preview")).headers["location"])
    resp = await authed.get(f"/api/media/1?w=480&preview={token}")
    assert resp.status_code == 200 and resp.headers["cache-control"] == "private, no-store"
    assert (await authed.get("/api/media/1?preview=bad")).status_code == 404


async def test_an_article_draft_preview(authed):
    await add_article(authed, title_en="Draft post", status="draft")
    assert (await authed.get("/api/articles/1")).status_code == 404
    resp = await authed.get("/admin/articles/1/preview")
    assert resp.status_code == 302 and "/th/articles/1?preview=" in resp.headers["location"]
    got = await authed.get(f"/api/preview/articles/1?token={token_of(resp.headers['location'])}")
    assert got.status_code == 200 and got.json()["title_en"] == "Draft post"


async def test_the_preview_buttons_are_on_the_forms_of_existing_entries_only(authed):
    await add_category(authed)
    await add_project(authed)
    await add_article(authed)
    # The admin host has no /admin prefix in its links: the proxy adds it.
    assert 'href="/projects/1/preview"' in (await authed.get("/admin/projects/1/edit")).text
    assert 'href="/articles/1/preview"' in (await authed.get("/admin/articles/1/edit")).text
    assert "/preview" not in (await authed.get("/admin/projects/new")).text


async def test_preview_routes_need_a_login(client):
    assert (await client.get("/admin/projects/1/preview")).status_code == 303
    assert (await client.get("/admin/articles/1/preview")).status_code == 303
