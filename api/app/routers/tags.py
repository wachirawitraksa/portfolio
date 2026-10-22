from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..forms import split_lines
from ..models import AuthSession, Tag
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/tags")


async def get_or_404(db: AsyncSession, tag_id: int) -> Tag:
    row = await db.get(Tag, tag_id)
    if row is None:
        raise HTTPException(404)
    return row


def form_page(request: Request, session: AuthSession, row, error: str | None = None, status: int = 200):
    return templates.TemplateResponse(
        request, "tag_form.html", {"row": row, "error": error, "csrf": session.csrf_token}, status_code=status
    )


@router.get("", response_class=HTMLResponse)
async def list_tags(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(Tag).order_by(Tag.name)
    query = query.where(Tag.deleted_at.is_not(None) if trash else Tag.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    return templates.TemplateResponse(request, "tags.html", {"rows": rows, "trash": trash, "csrf": session.csrf_token})


@router.get("/new", response_class=HTMLResponse)
async def new_form(request: Request, session: AuthSession = Depends(current_session)):
    return form_page(request, session, None)


@router.post("")
async def create(
    request: Request,
    name: str = Form(""),
    aliases: str = Form(""),
    group_th: str = Form(""),
    group_en: str = Form(""),
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    name = name.strip()
    if not name:
        return form_page(request, session, Tag(name="", aliases=split_lines(aliases), group_th=group_th, group_en=group_en), "ต้องกรอกชื่อ tag", 422)
    db.add(Tag(name=name, aliases=split_lines(aliases), group_th=group_th.strip()[:60], group_en=group_en.strip()[:60]))
    await db.commit()
    return go("/tags")


@router.get("/{tag_id}/edit", response_class=HTMLResponse)
async def edit_form(
    tag_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    return form_page(request, session, await get_or_404(db, tag_id))


@router.post("/{tag_id}")
async def update(
    tag_id: int,
    request: Request,
    name: str = Form(""),
    aliases: str = Form(""),
    group_th: str = Form(""),
    group_en: str = Form(""),
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, tag_id)
    name = name.strip()
    if not name:
        shown = Tag(id=row.id, name="", aliases=split_lines(aliases), group_th=group_th, group_en=group_en)
        return form_page(request, session, shown, "ต้องกรอกชื่อ tag", 422)
    row.name, row.aliases = name, split_lines(aliases)
    row.group_th, row.group_en = group_th.strip()[:60], group_en.strip()[:60]
    await db.commit()
    return go("/tags")


@router.post("/{tag_id}/trash")
async def trash(tag_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, tag_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/tags")


@router.post("/{tag_id}/restore")
async def restore(tag_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, tag_id)
    row.deleted_at = None
    await db.commit()
    return go("/tags?trash=true")
