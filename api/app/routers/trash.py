from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import AuthSession
from ..storage import Storage, get_storage
from ..templating import templates
from .. import trash
from .auth import go

router = APIRouter(prefix="/trash")


def entry_or_404(key: str) -> None:
    if key not in trash.ENTRIES:
        raise HTTPException(404)


@router.get("", response_class=HTMLResponse)
async def trash_page(
    request: Request,
    deleted: int = 0,
    skipped: int = 0,
    restored: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    groups = []
    for key, entry in trash.ENTRIES.items():
        rows = await trash.trashed(db, key)
        if rows:
            groups.append({"key": key, "label": entry.label, "rows": [(r, entry.title(r)) for r in rows]})
    context = {
        "groups": groups,
        "total": sum(len(g["rows"]) for g in groups),
        "deleted": deleted,
        "skipped": skipped,
        "restored": restored,
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "trash.html", context)


@router.post("/restore")
async def restore_item(
    kind: str = Form(...), item_id: int = Form(...), _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    entry_or_404(kind)
    if not await trash.restore(db, kind, item_id):
        raise HTTPException(404)
    return go("/trash?restored=true")


@router.post("/delete")
async def delete_item(
    kind: str = Form(...),
    item_id: int = Form(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    """Delete one item for good. Only an item that is already in the trash can be deleted this way."""
    entry_or_404(kind)
    deleted, skipped = await trash.purge(db, storage, kind, [item_id])
    if not deleted and not skipped:
        raise HTTPException(404)
    return go(f"/trash?deleted={deleted}&skipped={skipped}")


@router.post("/empty")
async def empty_trash(
    kind: str = Form("all"),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    """Delete for good everything in the trash, or everything of one kind."""
    if kind != "all":
        entry_or_404(kind)
    deleted = skipped = 0
    for key in trash.ENTRIES if kind == "all" else [kind]:
        d, s = await trash.purge(db, storage, key)
        deleted, skipped = deleted + d, skipped + s
    return go(f"/trash?deleted={deleted}&skipped={skipped}")
