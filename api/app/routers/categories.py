from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import AuthSession, Category, Project, project_category
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/categories")


async def get_or_404(db: AsyncSession, category_id: int) -> Category:
    row = await db.get(Category, category_id)
    if row is None:
        raise HTTPException(404)
    return row


@router.get("", response_class=HTMLResponse)
async def list_categories(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(Category).order_by(Category.sort_order, Category.id)
    query = query.where(Category.deleted_at.is_not(None) if trash else Category.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    return templates.TemplateResponse(
        request, "categories.html", {"rows": rows, "trash": trash, "csrf": session.csrf_token}
    )


@router.get("/new", response_class=HTMLResponse)
async def new_form(request: Request, session: AuthSession = Depends(current_session)):
    return templates.TemplateResponse(
        request, "category_form.html", {"row": None, "csrf": session.csrf_token}
    )


@router.post("")
async def create(
    name_th: str = Form(""),
    name_en: str = Form(""),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    last = (await db.execute(select(func.coalesce(func.max(Category.sort_order), 0)))).scalar_one()
    db.add(Category(name_th=name_th.strip(), name_en=name_en.strip(), sort_order=last + 1))
    await db.commit()
    return go("/categories")


@router.get("/{category_id}/edit", response_class=HTMLResponse)
async def edit_form(
    category_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, category_id)
    return templates.TemplateResponse(
        request, "category_form.html", {"row": row, "csrf": session.csrf_token}
    )


@router.post("/{category_id}")
async def update(
    category_id: int,
    name_th: str = Form(""),
    name_en: str = Form(""),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, category_id)
    row.name_th, row.name_en = name_th.strip(), name_en.strip()
    await db.commit()
    return go("/categories")


@router.post("/{category_id}/hide")
async def toggle_hidden(
    category_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_or_404(db, category_id)
    row.hidden = not row.hidden
    await db.commit()
    return go("/categories")


@router.post("/{category_id}/move")
async def move(
    category_id: int,
    direction: str = Form(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Category).where(Category.deleted_at.is_(None)).order_by(Category.sort_order, Category.id)
        )
    ).scalars().all()
    index = next((i for i, r in enumerate(rows) if r.id == category_id), None)
    if index is None:
        raise HTTPException(404)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(rows):
        rows[index], rows[swap] = rows[swap], rows[index]
    for position, row in enumerate(rows, start=1):
        row.sort_order = position
    await db.commit()
    return go("/categories")


@router.post("/{category_id}/trash")
async def trash(
    category_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_or_404(db, category_id)
    in_use = (
        await db.execute(
            select(func.count())
            .select_from(project_category)
            .join(Project, Project.id == project_category.c.project_id)
            .where(project_category.c.category_id == category_id, Project.deleted_at.is_(None))
        )
    ).scalar_one()
    if in_use:
        raise HTTPException(
            409,
            f"ลบไม่ได้ เพราะยังมีผลงาน {in_use} ชิ้นอยู่ในประเภทนี้ ย้ายผลงานออกก่อน หรือกด 'ซ่อน' ประเภทนี้แทน",
        )
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/categories")


@router.post("/{category_id}/restore")
async def restore(
    category_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_or_404(db, category_id)
    row.deleted_at = None
    row.hidden = True  # comes back hidden, so it is reviewed before it shows again
    await db.commit()
    return go("/categories?trash=true")
