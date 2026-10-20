from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import EDUCATION_LEVELS, AuthSession, EducationEntry
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/education")

SPANS = {"range": "เรียนจบแล้ว (มีเดือนที่สิ้นสุด)", "ongoing": "ยังเรียนอยู่"}
TEXT_PAIRS = ("institution", "degree", "field", "details")


def lines(text: str) -> list[str]:
    """One item per line. Commas stay inside the item."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def untranslated(row: EducationEntry) -> list[str]:
    """Fields filled in one language and empty in the other."""
    return [
        name
        for name in TEXT_PAIRS
        if bool(getattr(row, f"{name}_th").strip()) != bool(getattr(row, f"{name}_en").strip())
    ]


def period_text(row: EducationEntry) -> str:
    start = row.started_on.strftime("%Y-%m")
    return f"{start} – ปัจจุบัน" if row.ongoing else f"{start} – {row.ended_on.strftime('%Y-%m')}"


def parse_month(value: str) -> date | None:
    try:
        year, month = value.split("-")
        return date(int(year), int(month), 1)
    except ValueError:
        return None


async def get_or_404(db: AsyncSession, entry_id: int) -> EducationEntry:
    row = await db.get(EducationEntry, entry_id)
    if row is None:
        raise HTTPException(404)
    return row


def form_page(request, session, row, error=None, status=200):
    context = {
        "row": row,
        "levels": [(key, th) for key, (th, _) in EDUCATION_LEVELS.items()],
        "spans": list(SPANS.items()),
        "span": row.span if row else "range",
        "error": error,
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "education_form.html", context, status_code=status)


async def save(request, session, db, row: EducationEntry | None):
    form = await request.form()
    text = lambda key: str(form.get(key, "")).strip()  # noqa: E731
    span = text("span")
    values = {
        "institution_th": text("institution_th"),
        "institution_en": text("institution_en"),
        "level": text("level"),
        "degree_th": text("degree_th"),
        "degree_en": text("degree_en"),
        "field_th": text("field_th"),
        "field_en": text("field_en"),
        "grade": text("grade")[:60],
        "details_th": "\n".join(lines(text("details_th"))),
        "details_en": "\n".join(lines(text("details_en"))),
        "hidden": form.get("hidden") is not None,
        "started_on": parse_month(text("started_on")),
        "ended_on": parse_month(text("ended_on")) if span == "range" else None,
        "ongoing": span == "ongoing",
    }
    error = None
    if span not in SPANS:
        error = "ช่วงเวลาไม่ถูกต้อง"
    elif values["level"] not in EDUCATION_LEVELS:
        error = "ระดับการศึกษาไม่ถูกต้อง"
    elif not (values["institution_th"] or values["institution_en"]):
        error = "ต้องกรอกชื่อสถาบันอย่างน้อยหนึ่งภาษา"
    elif values["started_on"] is None:
        error = "ต้องเลือกเดือนที่เริ่มเรียน"
    elif span == "range" and values["ended_on"] is None:
        error = "ต้องเลือกเดือนที่สิ้นสุด"
    elif values["ended_on"] and values["ended_on"] < values["started_on"]:
        error = "เดือนที่สิ้นสุดต้องไม่ก่อนเดือนที่เริ่ม"
    if error:
        return form_page(request, session, EducationEntry(id=row.id if row else None, **values), error, 422)
    if row is None:
        db.add(EducationEntry(**values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
    await db.commit()
    return go("/education")


@router.get("", response_class=HTMLResponse)
async def list_entries(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(EducationEntry).order_by(EducationEntry.started_on.desc(), EducationEntry.id.desc())
    query = query.where(EducationEntry.deleted_at.is_not(None) if trash else EducationEntry.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    context = {
        "rows": rows,
        "trash": trash,
        "level_labels": {key: th for key, (th, _) in EDUCATION_LEVELS.items()},
        "periods": {r.id: period_text(r) for r in rows},
        "untranslated": {r.id: untranslated(r) for r in rows},
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "education.html", context)


@router.get("/new", response_class=HTMLResponse)
async def new_form(request: Request, session: AuthSession = Depends(current_session)):
    return form_page(request, session, None)


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
    return form_page(request, session, await get_or_404(db, entry_id))


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
    return go("/education")


@router.post("/{entry_id}/trash")
async def trash(entry_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, entry_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/education")


@router.post("/{entry_id}/restore")
async def restore(entry_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, entry_id)
    row.deleted_at = None
    row.hidden = True  # comes back hidden, so it is reviewed before it shows again
    await db.commit()
    return go("/education?trash=true")
