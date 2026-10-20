from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import AuthSession
from ..site import get_site_settings
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/settings")

# (field, label, hint)
FIELDS = (
    ("featured_limit", "ผลงานเด่นบนหน้าแรก", "จำนวนชิ้นที่ขึ้นหน้าแรก"),
    ("projects_page_size", "คลังผลงาน", "จำนวนชิ้นต่อหนึ่งครั้งที่โหลด"),
    ("articles_page_size", "บทความ", "จำนวนบทความต่อหนึ่งครั้งที่โหลด"),
)
MIN, MAX = 1, 60


async def page(request, session, row, error=None, status=200):
    context = {"row": row, "fields": FIELDS, "min": MIN, "max": MAX, "error": error, "csrf": session.csrf_token}
    return templates.TemplateResponse(request, "settings.html", context, status_code=status)


@router.get("", response_class=HTMLResponse)
async def show_page(
    request: Request, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)
):
    return await page(request, session, await get_site_settings(db))


@router.post("")
async def save(
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    row = await get_site_settings(db)
    values = {}
    for field, label, _hint in FIELDS:
        raw = str(form.get(field, "")).strip()
        if not (raw.isdigit() and MIN <= int(raw) <= MAX):
            return await page(request, session, row, f"{label}: ต้องเป็นตัวเลข {MIN}–{MAX}", 422)
        values[field] = int(raw)
    for field, value in values.items():
        setattr(row, field, value)
    await db.commit()
    return go("/settings")
