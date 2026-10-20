from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import EMPLOYMENT_TYPES, SPANS, AuthSession, Tag, WorkEntry
from ..templating import templates
from .auth import go
from .projects import resolve_tags

router = APIRouter(prefix="/work")

SPAN_LABELS = {"range": "ช่วงเวลา (มีวันเริ่มและวันสิ้นสุด)", "ongoing": "ยังทำอยู่", "moment": "วันเดียว"}


def bullet_lines(text: str) -> list[str]:
    """One bullet per line. Unlike tag lists, commas stay inside the bullet."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def untranslated(row: WorkEntry) -> list[str]:
    """Fields filled in one language and empty in the other."""
    return [
        name
        for name in ("position", "bullets")
        if bool(getattr(row, f"{name}_th").strip()) != bool(getattr(row, f"{name}_en").strip())
    ]


def period_text(row: WorkEntry) -> str:
    start = row.started_on.isoformat()
    if row.span == "ongoing":
        return f"{start} – ปัจจุบัน"
    if row.span == "moment":
        return start
    return f"{start} – {row.ended_on.isoformat()}"


def parse_day(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


async def get_or_404(db: AsyncSession, entry_id: int) -> WorkEntry:
    row = await db.get(WorkEntry, entry_id)
    if row is None:
        raise HTTPException(404)
    return row


async def form_page(request, session, db, row, tag_ids, error=None, status=200, new_tags=()):
    tags = (await db.execute(select(Tag).where(Tag.deleted_at.is_(None)).order_by(Tag.name))).scalars().all()
    context = {
        "row": row,
        "types": [(key, th) for key, (th, _) in EMPLOYMENT_TYPES.items()],
        "spans": list(SPAN_LABELS.items()),
        "span": row.span if row else "range",
        "chosen_tags": [{"value": t.id, "label": t.name, "new": False} for t in tags if t.id in tag_ids]
        + [{"value": n, "label": n, "new": True} for n in new_tags],
        "tag_options": [
            {"id": t.id, "label": t.name, "also": ", ".join(t.aliases), "names": [t.name, *t.aliases]} for t in tags
        ],
        "error": error,
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "work_form.html", context, status_code=status)


async def save(request, session, db, row: WorkEntry | None):
    form = await request.form()
    text = lambda key: str(form.get(key, "")).strip()  # noqa: E731
    span = text("span")
    values = {
        "position_th": text("position_th"),
        "position_en": text("position_en"),
        "employer": text("employer"),
        "employment_type": text("employment_type"),
        "bullets_th": "\n".join(bullet_lines(text("bullets_th"))),
        "bullets_en": "\n".join(bullet_lines(text("bullets_en"))),
        "hidden": form.get("hidden") is not None,
        "started_on": parse_day(text("started_on")),
        "ended_on": parse_day(text("ended_on")) if span == "range" else None,
        "ongoing": span == "ongoing",
    }
    error = None
    if span not in SPANS:
        error = "ช่วงเวลาไม่ถูกต้อง"
    elif values["employment_type"] not in EMPLOYMENT_TYPES:
        error = "รูปแบบงานไม่ถูกต้อง"
    elif not (values["position_th"] or values["position_en"]):
        error = "ต้องกรอกตำแหน่ง / หัวข้ออย่างน้อยหนึ่งภาษา"
    elif not values["employer"] and values["employment_type"] != "event":
        error = "ต้องกรอกที่ทำงาน"
    elif values["started_on"] is None:
        error = "ต้องเลือกวันที่เริ่ม" if span != "moment" else "ต้องเลือกวันที่"
    elif span == "range" and values["ended_on"] is None:
        error = "ต้องเลือกวันที่สิ้นสุด"
    elif values["ended_on"] and values["ended_on"] < values["started_on"]:
        error = "วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่ม"

    tag_ids = sorted({int(v) for v in form.getlist("tag_ids") if str(v).isdigit()})
    typed = [str(v).strip() for v in form.getlist("new_tags") if str(v).strip()]
    # Look tags up before a new row joins the session (a query autoflushes it).
    tags, new_tags = await resolve_tags(db, tag_ids, typed)
    if error:
        shown = WorkEntry(id=row.id if row else None, **values)
        return await form_page(request, session, db, shown, [t.id for t in tags], error, 422, new_tags)
    for tag in tags:
        tag.deleted_at = None  # typing a trashed tag's name brings it back
    for name in new_tags:
        tag = Tag(name=name, aliases=[])
        db.add(tag)
        tags.append(tag)
    if row is None:
        db.add(WorkEntry(tags=tags, **values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
        row.tags = tags
    await db.commit()
    return go("/work")


@router.get("", response_class=HTMLResponse)
async def list_entries(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkEntry).order_by(WorkEntry.started_on.desc(), WorkEntry.id.desc())
    query = query.where(WorkEntry.deleted_at.is_not(None) if trash else WorkEntry.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    context = {
        "rows": rows,
        "trash": trash,
        "type_labels": {key: th for key, (th, _) in EMPLOYMENT_TYPES.items()},
        "periods": {r.id: period_text(r) for r in rows},
        "untranslated": {r.id: untranslated(r) for r in rows},
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "work.html", context)


@router.get("/new", response_class=HTMLResponse)
async def new_form(
    request: Request, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)
):
    return await form_page(request, session, db, None, [])


@router.post("")
async def create(
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    return await save(request, session, db, None)


@router.get("/{entry_id}/edit", response_class=HTMLResponse)
async def edit_form(
    entry_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, entry_id)
    return await form_page(request, session, db, row, [t.id for t in row.tags])


@router.post("/{entry_id}")
async def update(
    entry_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    return await save(request, session, db, await get_or_404(db, entry_id))


@router.post("/{entry_id}/hide")
async def toggle_hidden(entry_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, entry_id)
    row.hidden = not row.hidden
    await db.commit()
    return go("/work")


@router.post("/{entry_id}/trash")
async def trash(entry_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, entry_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/work")


@router.post("/{entry_id}/restore")
async def restore(entry_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, entry_id)
    row.deleted_at = None
    row.hidden = True  # comes back hidden, so it is reviewed before it shows again
    await db.commit()
    return go("/work?trash=true")
