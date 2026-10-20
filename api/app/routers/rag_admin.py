from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import AuthSession, RagChunk
from ..rag.index import rebuild
from ..rag.search import retrieve
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/rag")

TYPE_LABELS = {"project": "ผลงาน", "work": "ประวัติการทำงาน", "article": "บทความ", "profile": "ข้อมูลส่วนตัว"}


@router.get("", response_class=HTMLResponse)
async def status_page(
    request: Request,
    done: bool = False,
    q: str = "",
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(RagChunk.source_type, func.count()).group_by(RagChunk.source_type))).all()
    built_at = (await db.execute(select(func.max(RagChunk.built_at)))).scalar_one()
    context = {
        "counts": [(TYPE_LABELS.get(kind, kind), n) for kind, n in sorted(rows)],
        "total": sum(n for _, n in rows),
        "built_at": built_at,
        "done": done,
        "q": q,
        # Try a question: shows what the search finds and how sure it is, without calling any model.
        "result": await retrieve(db, q) if q.strip() else None,
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "rag.html", context)


@router.post("/rebuild")
async def rebuild_index(_: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    await rebuild(db)
    return go("/rag?done=true")
