from .test_projects import add_tag, public


def work_data(c, **overrides):
    data = {
        "position_th": "วิศวกรซอฟต์แวร์",
        "position_en": "Software Engineer",
        "employer": "Acme",
        "employment_type": "full_time",
        "span": "range",
        "started_on": "2023-03-15",
        "ended_on": "2025-06-30",
        "bullets_th": "สร้างระบบสต็อก\nลดเวลานับของ",
        "bullets_en": "Built a stock system\nCut counting time",
        "csrf_token": c.csrf,
    }
    data.update(overrides)
    return data


async def add_work(c, **overrides):
    return await c.post("/admin/work", data=work_data(c, **overrides))


async def post(c, path):
    return await c.post(path, data={"csrf_token": c.csrf})


async def test_range_shows_in_admin_and_public_api(authed):
    assert (await add_work(authed)).status_code == 303
    page = (await authed.get("/admin/work")).text
    assert "Acme" in page and "2023-03-15 – 2025-06-30" in page
    item = (await public(authed, "/api/experience"))[0]
    assert item["position_en"] == "Software Engineer" and item["span"] == "range"
    assert item["started_on"] == "2023-03-15" and item["ended_on"] == "2025-06-30"
    assert item["employment_type_en"] == "Full-time"
    assert item["bullets_en"] == ["Built a stock system", "Cut counting time"]


async def test_ongoing_has_no_end_and_ignores_a_typed_end_date(authed):
    await add_work(authed, span="ongoing", ended_on="2030-01-01")
    item = (await public(authed, "/api/experience"))[0]
    assert item["span"] == "ongoing" and item["ended_on"] is None
    assert "ปัจจุบัน" in (await authed.get("/admin/work")).text


async def test_single_day_event_sits_inside_a_long_job(authed):
    await add_work(authed, employer="Acme", started_on="2022-01-10", ended_on="2025-12-31")
    await add_work(
        authed,
        employment_type="event",
        employer="",
        position_en="Hackathon",
        position_th="แฮ็กกาธอน",
        span="moment",
        started_on="2024-05-18",
        ended_on="",
    )
    items = await public(authed, "/api/experience")
    assert [i["position_en"] for i in items] == ["Hackathon", "Software Engineer"]  # newest start first
    event, job = items
    assert event["span"] == "moment" and event["started_on"] == event["ended_on"] == "2024-05-18"
    assert job["started_on"] <= event["started_on"] <= job["ended_on"]  # front end nests by dates
    assert "วันเดียว" in (await authed.get("/admin/work")).text


async def test_range_with_same_start_and_end_counts_as_a_moment(authed):
    await add_work(authed, started_on="2024-05-18", ended_on="2024-05-18")
    assert (await public(authed, "/api/experience"))[0]["span"] == "moment"


async def test_employer_is_optional_only_for_events(authed):
    assert (await add_work(authed, employer="")).status_code == 422
    assert (await add_work(authed, employer="", employment_type="event")).status_code == 303


async def test_tags_by_id_by_name_and_new(authed):
    await add_tag(authed, "PostgreSQL", "pg")
    await add_work(authed, tag_ids=["1"], new_tags=["pg", "Docker"])
    names = [t["name"] for t in (await public(authed, "/api/experience"))[0]["tags"]]
    assert names == ["Docker", "PostgreSQL"]  # "pg" matched the existing alias, Docker was created


async def test_validation_errors_keep_the_form(authed):
    for override, message in (
        ({"position_th": "", "position_en": ""}, "ต้องกรอกตำแหน่ง"),
        ({"started_on": ""}, "ต้องเลือกวันที่เริ่ม"),
        ({"span": "moment", "started_on": ""}, "ต้องเลือกวันที่"),
        ({"ended_on": ""}, "ต้องเลือกวันที่สิ้นสุด"),
        ({"started_on": "2025-05-01", "ended_on": "2025-01-01"}, "ต้องไม่ก่อนวันที่เริ่ม"),
        ({"started_on": "not-a-date"}, "ต้องเลือกวันที่เริ่ม"),
        ({"employment_type": "bogus"}, "รูปแบบงานไม่ถูกต้อง"),
        ({"span": "bogus"}, "ช่วงเวลาไม่ถูกต้อง"),
    ):
        resp = await add_work(authed, **override)
        assert resp.status_code == 422 and message in resp.text, override
    assert await public(authed, "/api/experience") == []


async def test_hide_trash_restore(authed):
    await add_work(authed)
    await post(authed, "/admin/work/1/hide")
    assert await public(authed, "/api/experience") == []
    await post(authed, "/admin/work/1/hide")
    assert len(await public(authed, "/api/experience")) == 1
    await post(authed, "/admin/work/1/trash")
    assert await public(authed, "/api/experience") == []
    assert "Acme" in (await authed.get("/admin/work?trash=true")).text
    await post(authed, "/admin/work/1/restore")
    assert await public(authed, "/api/experience") == []  # back hidden until reviewed


async def test_edit_switches_span_and_untranslated_is_flagged(authed):
    await add_work(authed, bullets_en="")
    assert "ยังไม่ได้แปล 1 ช่อง" in (await authed.get("/admin/work")).text
    await authed.post("/admin/work/1", data=work_data(authed, employer="Beta", span="ongoing"))
    item = (await public(authed, "/api/experience"))[0]
    assert item["employer"] == "Beta" and item["span"] == "ongoing" and item["ended_on"] is None


async def test_form_pages_render(authed):
    await add_work(authed)
    assert 'name="span"' in (await authed.get("/admin/work/new")).text
    edit = (await authed.get("/admin/work/1/edit")).text
    assert 'value="range" checked' in edit and 'value="2025-06-30"' in edit


async def test_mutations_need_csrf_and_login(authed, client):
    assert (await authed.post("/admin/work", data={"employer": "x"})).status_code == 403
    client.cookies.clear()
    assert (await client.get("/admin/work")).status_code == 303
