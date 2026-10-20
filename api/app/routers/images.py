import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_db
from ..deps import require_csrf
from ..models import Project, ProjectImage
from ..storage import Storage, get_storage
from .auth import go

router = APIRouter(prefix="/projects/{project_id}/images")
# Admin preview of any image, drafts included. The public copy is in public.py.
preview = APIRouter()

# The type comes from the file's own first bytes, never from what the browser claims.
SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
)


def sniff(data: bytes) -> tuple[str, str] | None:
    for magic, content_type, ext in SIGNATURES:
        if data.startswith(magic):
            return content_type, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


def image_response(data: bytes, content_type: str, cache: str) -> Response:
    return Response(
        data,
        media_type=content_type,
        headers={"Cache-Control": cache, "X-Content-Type-Options": "nosniff"},
    )


async def get_image(db: AsyncSession, project_id: int, image_id: int) -> ProjectImage:
    row = await db.get(ProjectImage, image_id)
    if row is None or row.project_id != project_id:
        raise HTTPException(404)
    return row


def back(project_id: int):
    return go(f"/projects/{project_id}/edit")


async def live_images(db: AsyncSession, project_id: int) -> list[ProjectImage]:
    return list(
        (
            await db.execute(
                select(ProjectImage)
                .where(ProjectImage.project_id == project_id, ProjectImage.deleted_at.is_(None))
                .order_by(ProjectImage.sort_order, ProjectImage.id)
            )
        ).scalars()
    )


async def ensure_one_cover(db: AsyncSession, project_id: int) -> None:
    rows = await live_images(db, project_id)
    if rows and not any(r.is_cover for r in rows):
        rows[0].is_cover = True


@router.post("")
async def upload(
    project_id: int,
    files: list[UploadFile] = File(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    if await db.get(Project, project_id) is None:
        raise HTTPException(404)
    max_mb = get_settings().max_upload_mb
    limit = max_mb * 1024 * 1024
    last = (
        await db.execute(
            select(func.coalesce(func.max(ProjectImage.sort_order), 0)).where(ProjectImage.project_id == project_id)
        )
    ).scalar_one()
    for offset, upload_file in enumerate(files, start=1):
        if not upload_file.filename:
            continue  # an empty file input still sends one blank part
        data = await upload_file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"ไฟล์ใหญ่เกิน {max_mb} MB")
        kind = sniff(data)
        if kind is None:
            raise HTTPException(415, "รับเฉพาะไฟล์ JPEG, PNG, GIF หรือ WebP")
        content_type, ext = kind
        key = f"projects/{project_id}/{uuid.uuid4().hex}.{ext}"
        await storage.put(key, data, content_type)
        db.add(
            ProjectImage(
                project_id=project_id,
                key=key,
                content_type=content_type,
                size=len(data),
                sort_order=last + offset,
            )
        )
    await db.flush()
    await ensure_one_cover(db, project_id)
    await db.commit()
    return back(project_id)


@router.post("/{image_id}/cover")
async def set_cover(
    project_id: int, image_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_image(db, project_id, image_id)
    if row.deleted_at is not None:
        raise HTTPException(404)
    for other in await live_images(db, project_id):
        other.is_cover = other.id == row.id
    await db.commit()
    return back(project_id)


@router.post("/{image_id}/caption")
async def set_caption(
    project_id: int,
    image_id: int,
    caption_th: str = Form(""),
    caption_en: str = Form(""),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    row = await get_image(db, project_id, image_id)
    row.caption_th = caption_th.strip()[:300]
    row.caption_en = caption_en.strip()[:300]
    await db.commit()
    return back(project_id)


@router.post("/{image_id}/move")
async def move(
    project_id: int,
    image_id: int,
    direction: str = Form(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    rows = await live_images(db, project_id)
    index = next((i for i, r in enumerate(rows) if r.id == image_id), None)
    if index is None:
        raise HTTPException(404)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(rows):
        rows[index], rows[swap] = rows[swap], rows[index]
    for position, row in enumerate(rows, start=1):
        row.sort_order = position
    await db.commit()
    return back(project_id)


@router.post("/{image_id}/trash")
async def trash(
    project_id: int, image_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_image(db, project_id, image_id)
    row.deleted_at = datetime.now(timezone.utc)
    row.is_cover = False
    await db.flush()
    await ensure_one_cover(db, project_id)
    await db.commit()
    return back(project_id)


@router.post("/{image_id}/restore")
async def restore(
    project_id: int, image_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_image(db, project_id, image_id)
    row.deleted_at = None
    await db.flush()
    await ensure_one_cover(db, project_id)
    await db.commit()
    return back(project_id)


@preview.get("/media/{image_id}")
async def show(image_id: int, db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)):
    row = await db.get(ProjectImage, image_id)
    data = await storage.get(row.key) if row else None
    if row is None or data is None:
        raise HTTPException(404)
    return image_response(data, row.content_type, "private, max-age=3600")
