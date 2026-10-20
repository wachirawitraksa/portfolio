import hashlib
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_db
from ..deps import current_session, require_csrf
from ..forms import is_http_url
from ..models import AuthSession, ContactLink
from ..site import get_profile
from ..storage import Storage, get_storage
from ..templating import templates
from .auth import go
from .images import image_response, sniff

router = APIRouter(prefix="/profile")

LANGS = ("th", "en")


def version(key: str) -> str:
    """Short tag for a stored file. The URL changes when the file does, so it can be cached for good."""
    return hashlib.sha1(key.encode()).hexdigest()[:8]


def file_response(data: bytes, content_type: str, cache: str, filename: str | None = None) -> Response:
    response = image_response(data, content_type, cache)
    if filename:
        response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


async def read_upload(upload: UploadFile) -> bytes:
    max_mb = get_settings().max_upload_mb
    limit = max_mb * 1024 * 1024
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"ไฟล์ใหญ่เกิน {max_mb} MB")
    return data


def untranslated(row) -> list[str]:
    return [
        name
        for name in ("name", "intro", "location")
        if bool(getattr(row, f"{name}_th").strip()) != bool(getattr(row, f"{name}_en").strip())
    ]


async def links(db: AsyncSession, trashed: bool = False) -> list[ContactLink]:
    query = select(ContactLink).order_by(ContactLink.sort_order, ContactLink.id)
    query = query.where(ContactLink.deleted_at.is_not(None) if trashed else ContactLink.deleted_at.is_(None))
    return list((await db.execute(query)).scalars())


async def page(request, session, db, error=None, status=200, shown=None):
    row = await get_profile(db)
    context = {
        "row": shown or row,
        "saved": row,
        "links": await links(db),
        "trashed_links": await links(db, trashed=True),
        "untranslated": untranslated(row),
        "error": error,
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "profile.html", context, status_code=status)


@router.get("", response_class=HTMLResponse)
async def show_page(
    request: Request, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)
):
    return await page(request, session, db)


@router.post("")
async def save(
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    values = {
        key: str(form.get(key, "")).strip()
        for key in ("name_th", "name_en", "intro_th", "intro_en", "location_th", "location_en", "email")
    }
    row = await get_profile(db)
    if values["email"] and ("@" not in values["email"] or " " in values["email"]):
        # Show what was typed, but leave the stored row untouched.
        shown = SimpleNamespace(**{**{c: getattr(row, c) for c in row.__table__.columns.keys()}, **values})
        return await page(request, session, db, "อีเมลไม่ถูกต้อง", 422, shown)
    for key, value in values.items():
        setattr(row, key, value)
    await db.commit()
    return go("/profile")


@router.get("/photo")
async def preview_photo(db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)):
    row = await get_profile(db)
    data = await storage.get(row.photo_key) if row.photo_key else None
    if data is None:
        raise HTTPException(404)
    return file_response(data, row.photo_content_type, "private, max-age=60")


@router.post("/photo")
async def upload_photo(
    file: UploadFile = File(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    data = await read_upload(file)
    kind = sniff(data)
    if kind is None:
        raise HTTPException(415, "รับเฉพาะไฟล์ JPEG, PNG, GIF หรือ WebP")
    content_type, ext = kind
    row = await get_profile(db)
    old = row.photo_key
    row.photo_key = f"profile/photo-{uuid.uuid4().hex}.{ext}"
    row.photo_content_type = content_type
    await storage.put(row.photo_key, data, content_type)
    await db.commit()
    if old:
        await storage.delete(old)
    return go("/profile")


@router.post("/photo/remove")
async def remove_photo(
    _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)
):
    row = await get_profile(db)
    old = row.photo_key
    row.photo_key = row.photo_content_type = ""
    await db.commit()
    if old:
        await storage.delete(old)
    return go("/profile")


def cv_fields(lang: str) -> tuple[str, str]:
    if lang not in LANGS:
        raise HTTPException(404)
    return f"cv_{lang}_key", f"cv_{lang}_name"


@router.get("/cv/{lang}")
async def preview_cv(lang: str, db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)):
    key_field, _ = cv_fields(lang)
    row = await get_profile(db)
    key = getattr(row, key_field)
    data = await storage.get(key) if key else None
    if data is None:
        raise HTTPException(404)
    return file_response(data, "application/pdf", "private, max-age=60", f"cv-{lang}.pdf")


@router.post("/cv/{lang}")
async def upload_cv(
    lang: str,
    file: UploadFile = File(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    key_field, name_field = cv_fields(lang)
    data = await read_upload(file)
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "CV ต้องเป็นไฟล์ PDF")
    row = await get_profile(db)
    old = getattr(row, key_field)
    setattr(row, key_field, f"profile/cv-{lang}-{uuid.uuid4().hex}.pdf")
    setattr(row, name_field, (file.filename or "cv.pdf")[:200])
    await storage.put(getattr(row, key_field), data, "application/pdf")
    await db.commit()
    if old:
        await storage.delete(old)
    return go("/profile")


@router.post("/cv/{lang}/remove")
async def remove_cv(
    lang: str,
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    key_field, name_field = cv_fields(lang)
    row = await get_profile(db)
    old = getattr(row, key_field)
    setattr(row, key_field, "")
    setattr(row, name_field, "")
    await db.commit()
    if old:
        await storage.delete(old)
    return go("/profile")


async def get_link_or_404(db: AsyncSession, link_id: int) -> ContactLink:
    row = await db.get(ContactLink, link_id)
    if row is None:
        raise HTTPException(404)
    return row


def check_link(label: str, url: str) -> str | None:
    if not label:
        return "ต้องกรอกชื่อช่องทาง เช่น GitHub"
    if not is_http_url(url):
        return "ลิงก์ต้องขึ้นต้นด้วย http:// หรือ https://"
    return None


@router.post("/links")
async def add_link(
    request: Request,
    label: str = Form(""),
    url: str = Form(""),
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    label, url = label.strip()[:80], url.strip()[:500]
    error = check_link(label, url)
    if error:
        return await page(request, session, db, error, 422)
    last = (await db.execute(select(func.coalesce(func.max(ContactLink.sort_order), 0)))).scalar_one()
    db.add(ContactLink(label=label, url=url, sort_order=last + 1))
    await db.commit()
    return go("/profile")


@router.post("/links/{link_id}")
async def update_link(
    link_id: int,
    request: Request,
    label: str = Form(""),
    url: str = Form(""),
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    row = await get_link_or_404(db, link_id)
    label, url = label.strip()[:80], url.strip()[:500]
    error = check_link(label, url)
    if error:
        return await page(request, session, db, error, 422)
    row.label, row.url = label, url
    await db.commit()
    return go("/profile")


@router.post("/links/{link_id}/move")
async def move_link(
    link_id: int,
    direction: str = Form(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    rows = await links(db)
    index = next((i for i, r in enumerate(rows) if r.id == link_id), None)
    if index is None:
        raise HTTPException(404)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(rows):
        rows[index], rows[swap] = rows[swap], rows[index]
    for position, row in enumerate(rows, start=1):
        row.sort_order = position
    await db.commit()
    return go("/profile")


@router.post("/links/{link_id}/trash")
async def trash_link(link_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_link_or_404(db, link_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/profile")


@router.post("/links/{link_id}/restore")
async def restore_link(link_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_link_or_404(db, link_id)
    row.deleted_at = None
    await db.commit()
    return go("/profile")
