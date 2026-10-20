from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..models import AuthSession, RagChunk, RagQuery
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


UNANSWERED = ("no_answer", "fallback")
FILTERS = {
    "unanswered": ("ตอบไม่ได้", UNANSWERED),
    "all": ("ทั้งหมด", None),
    "blocked": ("ถูกบล็อก / เบนไปอีเมล", ("blocked", "redirect")),
}
MODE_LABELS = {
    "answer": "ตอบ (มั่นใจสูง)",
    "uncertain": "ตอบ (ไม่การันตี)",
    "no_answer": "ไม่มีข้อมูลบนเว็บ",
    "fallback": "สรุปไม่ได้ (โมเดลไม่พร้อม)",
    "redirect": "เบนไปอีเมล",
    "greeting": "ทักทาย",
    "blocked": "ถูกบล็อก",
}


@router.get("/questions", response_class=HTMLResponse)
async def questions_page(
    request: Request,
    show: str = "unanswered",
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    """What visitors asked. The unanswered ones are the list of content still worth writing."""
    show = show if show in FILTERS else "unanswered"
    modes = FILTERS[show][1]
    query = select(RagQuery).order_by(RagQuery.id.desc()).limit(100)
    if modes:
        query = query.where(RagQuery.mode.in_(modes))
    rows = (await db.execute(query)).scalars().all()
    repeated = (
        await db.execute(
            select(RagQuery.normalized, func.count().label("n"), func.max(RagQuery.created_at))
            .where(RagQuery.mode.in_(UNANSWERED), RagQuery.normalized != "")
            .group_by(RagQuery.normalized)
            .order_by(func.count().desc(), func.max(RagQuery.created_at).desc())
            .limit(15)
        )
    ).all()
    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    today = (
        await db.execute(
            select(RagQuery.tier, RagQuery.cached, func.count())
            .where(RagQuery.created_at > day_ago)
            .group_by(RagQuery.tier, RagQuery.cached)
        )
    ).all()
    context = {
        "rows": rows,
        "show": show,
        "filters": {key: label for key, (label, _) in FILTERS.items()},
        "mode_labels": MODE_LABELS,
        "repeated": repeated,
        "asked_today": sum(n for _, _, n in today),
        "model_calls_today": sum(n for tier, cached, n in today if tier and not cached),
        "cached_today": sum(n for _, cached, n in today if cached),
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "rag_questions.html", context)


@router.post("/rebuild")
async def rebuild_index(_: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    await rebuild(db)
    return go("/rag?done=true")
