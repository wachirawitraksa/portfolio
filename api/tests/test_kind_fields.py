import json
import re

from sqlalchemy import select

from app.db import SessionLocal
from app.models import KIND_FIELD_GROUPS, Kind

from .test_projects import add_category, add_project

EVERY_GROUP = list(KIND_FIELD_GROUPS)
CERTIFICATE = ["credential", "year"]
PROJECT = ["tech", "story", "links", "year"]


async def post(c, path, **data):
    return await c.post(path, data={"csrf_token": c.csrf, **data})


async def add_kind(c, name, groups=None):
    """Like the admin form: it always sends the marker and the ticked groups."""
    data = {"name_en": name, "name_th": name}
    if groups is not None:
        data["fields_sent"] = "1"
        data["fields"] = groups
    return await post(c, "/admin/kinds", **data)


async def stored(kind_id):
    async with SessionLocal() as db:
        return (await db.get(Kind, kind_id)).fields


def element(page, group):
    """The opening tag of the element that carries data-group=<group>."""
    return re.search(rf"<[a-z]+[^>]*data-group=\"{group}\"[^>]*>", page).group(0)


def is_hidden(page, group):
    return " hidden" in element(page, group)


def kind_map(page):
    return {int(k): v for k, v in json.loads(re.search(r"data-kind-fields='([^']*)'", page).group(1)).items()}


# --- choosing the groups on the kind form ------------------------------------------------------------


async def test_a_new_kind_made_without_the_form_keeps_every_group(authed):
    await add_kind(authed, "Quick")  # an old-style request: nothing about fields
    assert await stored(1) == EVERY_GROUP


async def test_the_form_saves_the_ticked_groups_in_menu_order(authed):
    await add_kind(authed, "Certificate", ["year", "credential"])
    assert await stored(1) == ["credential", "year"]
    await add_kind(authed, "Plain", [])  # form sent, nothing ticked
    assert await stored(2) == []
    await add_kind(authed, "Sneaky", ["story", "<script>", "nonsense"])
    assert await stored(3) == ["story"]  # unknown keys are dropped


async def test_editing_changes_the_groups_but_a_bare_edit_leaves_them(authed):
    await add_kind(authed, "Thing", PROJECT)
    await post(authed, "/admin/kinds/1", name_en="Renamed", name_th="เปลี่ยนชื่อ")  # no marker: groups untouched
    assert await stored(1) == PROJECT
    await post(authed, "/admin/kinds/1", name_en="Renamed", name_th="x", fields_sent="1", fields=["links"])
    assert await stored(1) == ["links"]


async def test_the_kind_form_shows_what_is_ticked(authed):
    new = (await authed.get("/admin/kinds/new")).text
    assert new.count('name="fields"') == len(EVERY_GROUP) and new.count("checked") == len(EVERY_GROUP)
    assert 'name="fields_sent"' in new
    await add_kind(authed, "Certificate", CERTIFICATE)
    edit = (await authed.get("/admin/kinds/1/edit")).text
    checked = re.findall(r'name="fields" value="(\w+)" checked', edit)
    assert checked == CERTIFICATE
    assert 'value="story" checked' not in edit and 'value="story"' in edit


async def test_the_kinds_list_says_which_groups_each_kind_uses(authed):
    await add_kind(authed, "Certificate", CERTIFICATE)
    await add_kind(authed, "Plain", [])
    page = (await authed.get("/admin/kinds")).text
    assert "ช่องที่ใช้" in page and "ใบเซอร์ / รางวัล" in page and "เฉพาะช่องพื้นฐาน" in page


# --- the entry form follows the kind ---------------------------------------------------------------------


async def setup_kinds(c):
    await add_kind(c, "Certificate", CERTIFICATE)  # id 1, first in the list
    await add_kind(c, "Project", PROJECT)  # id 2
    await add_category(c)


async def test_the_new_entry_form_starts_with_the_first_kinds_groups(authed):
    await setup_kinds(authed)
    page = (await authed.get("/admin/projects/new")).text
    assert not is_hidden(page, "credential") and not is_hidden(page, "year")
    for group in ("story", "tech", "links"):
        assert is_hidden(page, group), group


async def test_an_existing_entry_opens_with_its_own_kinds_groups(authed):
    await setup_kinds(authed)
    await add_project(authed, kind_id="2")
    page = (await authed.get("/admin/projects/1/edit")).text
    for group in PROJECT:
        assert not is_hidden(page, group), group
    assert is_hidden(page, "credential")


async def test_the_page_carries_what_the_script_needs_to_switch_groups(authed):
    await setup_kinds(authed)
    page = (await authed.get("/admin/projects/new")).text
    assert kind_map(page) == {1: CERTIFICATE, 2: PROJECT}
    assert 'id="hidden-note"' in page and 'select.addEventListener("change", sync)' in page
    assert set(json.loads(re.search(r"data-labels='([^']*)'", page).group(1))) == set(EVERY_GROUP)


async def test_data_in_a_group_the_kind_hides_is_kept_and_flagged(authed):
    await setup_kinds(authed)
    await add_project(authed, kind_id="2", problem_th="โจทย์", repo_url="https://github.com/me/x", year="2024")
    # The owner switches the entry to the certificate kind. The form still sends the hidden fields.
    await post(
        authed, "/admin/projects/1", title_th="ระบบสต็อก", title_en="Stock system", problem_th="โจทย์",
        repo_url="https://github.com/me/x", year="2024", kind_id="1", status="published", category_ids="1",
    )
    page = (await authed.get("/admin/projects/1/edit")).text
    assert is_hidden(page, "story") and is_hidden(page, "links")
    filled = json.loads(re.search(r"data-filled='([^']*)'", page).group(1))
    assert {"story", "links", "year"} <= set(filled)  # the script uses this to name the hidden groups
    assert "โจทย์" in page and "https://github.com/me/x" in page  # still in the page, just not shown
    async with SessionLocal() as db:
        from app.models import Project

        project = (await db.execute(select(Project))).scalar_one()
        assert project.problem_th == "โจทย์" and project.repo_url == "https://github.com/me/x" and project.kind_id == 1


async def test_without_any_kind_nothing_is_hidden(authed):
    page = (await authed.get("/admin/projects/new")).text
    assert 'id="kind_id"' not in page and "เพิ่มชนิดก่อน" in page
    for group in EVERY_GROUP:
        assert not is_hidden(page, group), group


async def test_a_kind_with_every_group_hides_nothing(authed):
    await add_kind(authed, "Everything")
    page = (await authed.get("/admin/projects/new")).text
    for group in EVERY_GROUP:
        assert not is_hidden(page, group), group


async def test_a_validation_error_keeps_the_chosen_kinds_groups(authed):
    await setup_kinds(authed)
    resp = await post(authed, "/admin/projects", kind_id="1", title_th="", title_en="")  # no title: refused
    assert resp.status_code == 422
    assert not is_hidden(resp.text, "credential") and is_hidden(resp.text, "story")


async def test_the_always_there_fields_are_never_hidden(authed):
    await add_kind(authed, "Bare", [])
    page = (await authed.get("/admin/projects/new")).text
    for name in ('name="title_th"', 'name="status"', 'name="aliases"', 'name="kind_id"'):
        assert name in page
    assert 'id="cat"' in page  # categories stay
    for group in EVERY_GROUP:
        assert is_hidden(page, group), group
