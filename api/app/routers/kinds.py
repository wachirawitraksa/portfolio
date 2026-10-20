from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import KIND_FIELD_GROUPS, AuthSession, Kind, Project
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/kinds")


async def get_or_404(db: AsyncSession, kind_id: int) -> Kind:
    row = await db.get(Kind, kind_id)
    if row is None:
        raise HTTPException(404)
    return row


@router.get("", response_class=HTMLResponse)
async def list_kinds(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(Kind).order_by(Kind.sort_order, Kind.id)
    query = query.where(Kind.deleted_at.is_not(None) if trash else Kind.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    context = {"rows": rows, "trash": trash, "groups": KIND_FIELD_GROUPS, "csrf": session.csrf_token}
    return templates.TemplateResponse(request, "kinds.html", context)


def chosen_groups(sent: str, picked: list[str]) -> list[str]:
    """The groups ticked in the form, in menu order. A request that did not come from the form
    (no `fields_sent` marker) keeps every group, so nothing is hidden by accident."""
    if not sent:
        return list(KIND_FIELD_GROUPS)
    return [key for key in KIND_FIELD_GROUPS if key in picked]


def form_page(request, session, row):
    context = {"row": row, "groups": KIND_FIELD_GROUPS, "csrf": session.csrf_token}
    return templates.TemplateResponse(request, "kind_form.html", context)


@router.get("/new", response_class=HTMLResponse)
async def new_form(request: Request, session: AuthSession = Depends(current_session)):
    return form_page(request, session, None)


@router.post("")
async def create(
    name_th: str = Form(""),
    name_en: str = Form(""),
    fields_sent: str = Form(""),
    fields: list[str] = Form([]),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    last = (await db.execute(select(func.coalesce(func.max(Kind.sort_order), 0)))).scalar_one()
    db.add(
        Kind(
            name_th=name_th.strip(),
            name_en=name_en.strip(),
            sort_order=last + 1,
            fields=chosen_groups(fields_sent, fields),
        )
    )
    await db.commit()
    return go("/kinds")


@router.get("/{kind_id}/edit", response_class=HTMLResponse)
async def edit_form(
    kind_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    return form_page(request, session, await get_or_404(db, kind_id))


@router.post("/{kind_id}")
async def update(
    kind_id: int,
    name_th: str = Form(""),
    name_en: str = Form(""),
    fields_sent: str = Form(""),
    fields: list[str] = Form([]),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, kind_id)
    row.name_th, row.name_en = name_th.strip(), name_en.strip()
    if fields_sent:  # an edit that did not come from the form leaves the groups alone
        row.fields = chosen_groups(fields_sent, fields)
    await db.commit()
    return go("/kinds")


@router.post("/{kind_id}/hide")
async def toggle_hidden(
    kind_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_or_404(db, kind_id)
    row.hidden = not row.hidden
    await db.commit()
    return go("/kinds")


@router.post("/{kind_id}/move")
async def move(
    kind_id: int,
    direction: str = Form(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Kind).where(Kind.deleted_at.is_(None)).order_by(Kind.sort_order, Kind.id)
        )
    ).scalars().all()
    index = next((i for i, r in enumerate(rows) if r.id == kind_id), None)
    if index is None:
        raise HTTPException(404)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(rows):
        rows[index], rows[swap] = rows[swap], rows[index]
    for position, row in enumerate(rows, start=1):
        row.sort_order = position
    await db.commit()
    return go("/kinds")


@router.post("/{kind_id}/trash")
async def trash(
    kind_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_or_404(db, kind_id)
    in_use = (
        await db.execute(
            select(func.count()).select_from(Project).where(Project.kind_id == kind_id, Project.deleted_at.is_(None))
        )
    ).scalar_one()
    if in_use:
        raise HTTPException(
            409,
            f"ลบไม่ได้ เพราะยังมีรายการ {in_use} ชิ้นเป็นชนิดนี้ เปลี่ยนชนิดของรายการเหล่านั้นก่อน หรือกด 'ซ่อน' ชนิดนี้แทน",
        )
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/kinds")


@router.post("/{kind_id}/restore")
async def restore(
    kind_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_or_404(db, kind_id)
    row.deleted_at = None
    row.hidden = True  # comes back hidden, so it is reviewed before it shows again
    await db.commit()
    return go("/kinds?trash=true")
