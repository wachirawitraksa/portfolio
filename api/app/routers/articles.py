from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..forms import is_http_url
from ..models import ARTICLE_SOURCES, STATUSES, Article, AuthSession, Tag
from ..previews import mint, site_base
from ..templating import templates
from .auth import go
from .projects import STATUS_LABELS, resolve_tags

router = APIRouter(prefix="/articles")

SOURCE_LABELS = {"internal": "เขียนในเว็บนี้", "external": "ลิงก์ไปแพลตฟอร์มอื่น"}


def untranslated(row: Article) -> list[str]:
    """Fields filled in one language and empty in the other."""
    return [
        name
        for name in ("title", "summary", "body")
        if bool(getattr(row, f"{name}_th").strip()) != bool(getattr(row, f"{name}_en").strip())
    ]


async def get_or_404(db: AsyncSession, article_id: int) -> Article:
    row = await db.get(Article, article_id)
    if row is None:
        raise HTTPException(404)
    return row


async def form_page(request, session, db, row, tag_ids, error=None, status=200, new_tags=()):
    tags = (await db.execute(select(Tag).where(Tag.deleted_at.is_(None)).order_by(Tag.name))).scalars().all()
    context = {
        "row": row,
        "sources": list(SOURCE_LABELS.items()),
        "statuses": [(s, STATUS_LABELS[s]) for s in STATUSES],
        "chosen_tags": [{"value": t.id, "label": t.name, "new": False} for t in tags if t.id in tag_ids]
        + [{"value": n, "label": n, "new": True} for n in new_tags],
        "tag_options": [
            {"id": t.id, "label": t.name, "also": ", ".join(t.aliases), "names": [t.name, *t.aliases]} for t in tags
        ],
        "error": error,
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "article_form.html", context, status_code=status)


async def save(request, session, db, row: Article | None):
    form = await request.form()
    text = lambda key: str(form.get(key, "")).strip()  # noqa: E731
    values = {
        "title_th": text("title_th"),
        "title_en": text("title_en"),
        "summary_th": text("summary_th"),
        "summary_en": text("summary_en"),
        "body_th": text("body_th"),
        "body_en": text("body_en"),
        "source": text("source"),
        "external_url": text("external_url"),
        "platform": text("platform"),
        "status": text("status") or "draft",
        "published_on": None,
    }
    error = None
    if text("published_on"):
        try:
            values["published_on"] = date.fromisoformat(text("published_on"))
        except ValueError:
            error = "วันที่ไม่ถูกต้อง"
    if not error:
        if not (values["title_th"] or values["title_en"]):
            error = "ต้องกรอกชื่อบทความอย่างน้อยหนึ่งภาษา"
        elif values["source"] not in ARTICLE_SOURCES:
            error = "ชนิดบทความไม่ถูกต้อง"
        elif values["status"] not in STATUSES:
            error = "สถานะไม่ถูกต้อง"
        elif values["source"] == "external" and not is_http_url(values["external_url"]):
            error = "ลิงก์บทความต้องขึ้นต้นด้วย http:// หรือ https://"
        elif values["source"] == "external" and not values["platform"]:
            error = "ต้องกรอกชื่อแพลตฟอร์ม เช่น Medium"
        elif values["source"] == "internal" and not (values["body_th"] or values["body_en"]):
            error = "บทความที่เขียนในเว็บต้องมีเนื้อหาอย่างน้อยหนึ่งภาษา"
    if values["source"] == "internal":
        values["external_url"] = values["platform"] = ""
    elif values["source"] == "external":
        values["body_th"] = values["body_en"] = ""

    tag_ids = sorted({int(v) for v in form.getlist("tag_ids") if str(v).isdigit()})
    typed = [str(v).strip() for v in form.getlist("new_tags") if str(v).strip()]
    # Look tags up before a new row joins the session (a query autoflushes it).
    tags, new_tags = await resolve_tags(db, tag_ids, typed)
    if error:
        shown = Article(id=row.id if row else None, **values)
        return await form_page(request, session, db, shown, [t.id for t in tags], error, 422, new_tags)
    for tag in tags:
        tag.deleted_at = None  # typing a trashed tag's name brings it back
    for name in new_tags:
        tag = Tag(name=name, aliases=[])
        db.add(tag)
        tags.append(tag)
    if row is None:
        db.add(Article(tags=tags, **values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
        row.tags = tags
    await db.commit()
    return go("/articles")


@router.get("", response_class=HTMLResponse)
async def list_articles(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(Article).order_by(Article.published_on.desc().nulls_first(), Article.id.desc())
    query = query.where(Article.deleted_at.is_not(None) if trash else Article.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    context = {
        "rows": rows,
        "trash": trash,
        "status_labels": STATUS_LABELS,
        "source_labels": SOURCE_LABELS,
        "untranslated": {r.id: untranslated(r) for r in rows},
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "articles.html", context)


@router.get("/new", response_class=HTMLResponse)
async def new_form(
    request: Request, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)
):
    return await form_page(request, session, db, None, [])


@router.post("")
async def create(
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    return await save(request, session, db, None)


@router.get("/{article_id}/edit", response_class=HTMLResponse)
async def edit_form(
    article_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, article_id)
    return await form_page(request, session, db, row, [t.id for t in row.tags])


@router.get("/{article_id}/preview")
async def preview(
    article_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    """Open this entry on the real website, drafts included. The link works for a few minutes."""
    row = await get_or_404(db, article_id)
    token = await mint(db, "article", row.id)
    lang = "en" if request.cookies.get("lang") == "en" else "th"
    return RedirectResponse(f"{site_base(request)}/{lang}/articles/{row.id}?preview={token}", status_code=302)


@router.post("/{article_id}")
async def update(
    article_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    return await save(request, session, db, await get_or_404(db, article_id))


@router.post("/{article_id}/trash")
async def trash(article_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, article_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/articles")


@router.post("/{article_id}/restore")
async def restore(article_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, article_id)
    row.deleted_at = None
    row.status = "hidden"  # comes back hidden, so it is reviewed before it shows again
    await db.commit()
    return go("/articles?trash=true")
