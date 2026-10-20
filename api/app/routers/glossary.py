from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..forms import split_lines
from ..models import AuthSession, GlossaryEntry
from ..rag import knowledge
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/glossary")

MIN_TERMS = 2


async def get_or_404(db: AsyncSession, entry_id: int) -> GlossaryEntry:
    row = await db.get(GlossaryEntry, entry_id)
    if row is None:
        raise HTTPException(404)
    return row


def form_page(request: Request, session: AuthSession, row, error: str | None = None, status: int = 200):
    return templates.TemplateResponse(
        request, "glossary_form.html", {"row": row, "error": error, "csrf": session.csrf_token}, status_code=status
    )


@router.get("", response_class=HTMLResponse)
async def list_entries(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(GlossaryEntry).order_by(GlossaryEntry.id)
    query = query.where(GlossaryEntry.deleted_at.is_not(None) if trash else GlossaryEntry.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    return templates.TemplateResponse(
        request, "glossary.html", {"rows": rows, "trash": trash, "csrf": session.csrf_token}
    )


@router.get("/new", response_class=HTMLResponse)
async def new_form(request: Request, session: AuthSession = Depends(current_session)):
    return form_page(request, session, None)


@router.post("")
async def create(
    request: Request,
    terms: str = Form(""),
    note: str = Form(""),
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    words = split_lines(terms)
    if len(words) < MIN_TERMS:
        shown = GlossaryEntry(terms=words, note=note.strip())
        return form_page(request, session, shown, f"ใส่คำที่มีความหมายเดียวกันอย่างน้อย {MIN_TERMS} คำ", 422)
    db.add(GlossaryEntry(terms=words, note=note.strip()[:200]))
    await db.commit()
    knowledge.invalidate()
    return go("/glossary")


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
    terms: str = Form(""),
    note: str = Form(""),
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, entry_id)
    words = split_lines(terms)
    if len(words) < MIN_TERMS:
        shown = GlossaryEntry(id=row.id, terms=words, note=note.strip())
        return form_page(request, session, shown, f"ใส่คำที่มีความหมายเดียวกันอย่างน้อย {MIN_TERMS} คำ", 422)
    row.terms, row.note = words, note.strip()[:200]
    await db.commit()
    knowledge.invalidate()
    return go("/glossary")


@router.post("/{entry_id}/trash")
async def trash(entry_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, entry_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    knowledge.invalidate()
    return go("/glossary")


@router.post("/{entry_id}/restore")
async def restore(entry_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, entry_id)
    row.deleted_at = None
    await db.commit()
    knowledge.invalidate()
    return go("/glossary?trash=true")
