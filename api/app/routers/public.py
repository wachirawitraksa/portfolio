from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import (
    EMPLOYMENT_TYPES,
    PROJECT_TEXT_FIELDS,
    Article,
    Category,
    Kind,
    Project,
    ProjectImage,
    Tag,
    WorkEntry,
    project_category,
    project_tag,
)
from ..storage import Storage, get_storage
from .images import image_response

router = APIRouter()

# Only the fields a card needs. The detail view returns every text field.
CARD_TEXT_FIELDS = ("title", "problem")


def visible() -> list:
    return [Project.status == "published", Project.deleted_at.is_(None)]


def image_json(i: ProjectImage) -> dict:
    return {
        "id": i.id,
        "url": f"/api/media/{i.id}",
        "caption_th": i.caption_th,
        "caption_en": i.caption_en,
        "is_cover": i.is_cover,
    }


def project_json(p: Project, fields: tuple[str, ...], detail: bool = False) -> dict:
    cover = next((i for i in p.images if i.is_cover), p.images[0] if p.images else None)
    data: dict = {
        "cover_url": f"/api/media/{cover.id}" if cover else None,
        "id": p.id,
        "year": p.year,
        "repo_url": p.repo_url,
        "demo_url": p.demo_url,
        "verify_url": p.verify_url,
        "issuer": p.issuer,
        "issued_on": p.issued_on.isoformat() if p.issued_on else None,
        "featured": p.featured,
        "kind": {"id": p.kind.id, "name_th": p.kind.name_th, "name_en": p.kind.name_en}
        if p.kind and not p.kind.hidden and p.kind.deleted_at is None
        else None,
    }
    for name in fields:
        data[f"{name}_th"] = getattr(p, f"{name}_th")
        data[f"{name}_en"] = getattr(p, f"{name}_en")
    data["categories"] = [
        {"id": c.id, "name_th": c.name_th, "name_en": c.name_en}
        for c in p.categories
        if not c.hidden and c.deleted_at is None
    ]
    data["tags"] = [{"id": t.id, "name": t.name} for t in p.tags if t.deleted_at is None]
    if detail:
        data["images"] = [image_json(i) for i in p.images]
    return data


@router.get("/categories")
async def categories(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Category)
            .where(Category.hidden.is_(False), Category.deleted_at.is_(None))
            .order_by(Category.sort_order, Category.id)
        )
    ).scalars().all()
    return [{"id": r.id, "name_th": r.name_th, "name_en": r.name_en} for r in rows]


@router.get("/kinds")
async def kinds(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Kind)
            .where(Kind.hidden.is_(False), Kind.deleted_at.is_(None))
            .order_by(Kind.sort_order, Kind.id)
        )
    ).scalars().all()
    return [{"id": r.id, "name_th": r.name_th, "name_en": r.name_en} for r in rows]


@router.get("/tags")
async def tags(db: AsyncSession = Depends(get_db)):
    """Tags used by at least one public project, for the filter list."""
    count = func.count(Project.id)
    rows = (
        await db.execute(
            select(Tag, count)
            .join(project_tag, project_tag.c.tag_id == Tag.id)
            .join(Project, Project.id == project_tag.c.project_id)
            .where(Tag.deleted_at.is_(None), *visible())
            .group_by(Tag.id)
            .order_by(Tag.name)
        )
    ).all()
    return [{"id": tag.id, "name": tag.name, "count": n} for tag, n in rows]


@router.get("/projects")
async def projects(
    q: Annotated[str, Query(max_length=100)] = "",
    tag: Annotated[list[int], Query()] = [],
    category: int | None = None,
    kind: int | None = None,
    sort: Literal["order", "newest", "oldest"] = "order",
    limit: Annotated[int, Query(ge=1, le=60)] = 12,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
):
    """Public project list. Every tag given must match (narrowing, not widening)."""
    where = visible()
    q = q.strip()
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        text_columns = [getattr(Project, f"{n}_{lang}") for n in ("title", "problem", "work") for lang in ("th", "en")]
        tag_match = exists(
            select(1)
            .select_from(project_tag.join(Tag, Tag.id == project_tag.c.tag_id))
            .where(
                project_tag.c.project_id == Project.id,
                Tag.deleted_at.is_(None),
                or_(
                    Tag.name.ilike(like, escape="\\"),
                    func.array_to_string(Tag.aliases, " ").ilike(like, escape="\\"),
                ),
            )
        )
        where.append(
            or_(
                *[c.ilike(like, escape="\\") for c in text_columns],
                func.array_to_string(Project.aliases, " ").ilike(like, escape="\\"),
                tag_match,
            )
        )
    for tag_id in tag:
        where.append(
            exists(
                select(1)
                .select_from(project_tag.join(Tag, Tag.id == project_tag.c.tag_id))
                .where(project_tag.c.project_id == Project.id, project_tag.c.tag_id == tag_id, Tag.deleted_at.is_(None))
            )
        )
    if kind is not None:
        where.append(Project.kind_id == kind)
    if category is not None:
        where.append(
            exists(
                select(1).where(project_category.c.project_id == Project.id, project_category.c.category_id == category)
            )
        )

    order = {
        "order": (Project.sort_order, Project.id),
        "newest": (Project.year.desc().nulls_last(), Project.id.desc()),
        "oldest": (Project.year.asc().nulls_last(), Project.id),
    }[sort]
    total = (await db.execute(select(func.count()).select_from(Project).where(*where))).scalar_one()
    rows = (await db.execute(select(Project).where(*where).order_by(*order).limit(limit).offset(offset))).scalars().all()
    return {"total": total, "items": [project_json(p, CARD_TEXT_FIELDS) for p in rows]}


@router.get("/projects/featured")
async def featured(limit: Annotated[int, Query(ge=1, le=60)] = 6, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Project)
            .where(*visible(), Project.featured.is_(True))
            .order_by(Project.sort_order, Project.id)
            .limit(limit)
        )
    ).scalars().all()
    return [project_json(p, CARD_TEXT_FIELDS) for p in rows]


@router.get("/projects/{project_id}")
async def project(project_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Project).where(Project.id == project_id, *visible()))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404)
    return project_json(row, PROJECT_TEXT_FIELDS, detail=True)


@router.get("/experience")
async def experience(db: AsyncSession = Depends(get_db)):
    """Timeline items, newest start first. Long ranges, ongoing work and single days share one list;
    the front end nests a short item inside a long one by comparing dates.
    Hidden and trashed entries stay out."""
    rows = (
        await db.execute(
            select(WorkEntry)
            .where(WorkEntry.hidden.is_(False), WorkEntry.deleted_at.is_(None))
            .order_by(WorkEntry.started_on.desc(), WorkEntry.id.desc())
        )
    ).scalars().all()
    return [
        {
            "id": w.id,
            "position_th": w.position_th,
            "position_en": w.position_en,
            "employer": w.employer,
            "employment_type": w.employment_type,
            "employment_type_th": EMPLOYMENT_TYPES[w.employment_type][0],
            "employment_type_en": EMPLOYMENT_TYPES[w.employment_type][1],
            "span": w.span,  # range | ongoing | moment
            "started_on": w.started_on.isoformat(),
            # ongoing: null. moment: same day as started_on.
            "ended_on": None if w.span == "ongoing" else (w.ended_on or w.started_on).isoformat(),
            "bullets_th": w.bullets_th.splitlines(),
            "bullets_en": w.bullets_en.splitlines(),
            "tags": [{"id": t.id, "name": t.name} for t in w.tags if t.deleted_at is None],
        }
        for w in rows
    ]


def article_json(a: Article, detail: bool = False) -> dict:
    data = {
        "id": a.id,
        "title_th": a.title_th,
        "title_en": a.title_en,
        "summary_th": a.summary_th,
        "summary_en": a.summary_en,
        "source": a.source,
        "platform": a.platform,
        "external_url": a.external_url,
        "published_on": a.published_on.isoformat() if a.published_on else None,
        "tags": [{"id": t.id, "name": t.name} for t in a.tags if t.deleted_at is None],
    }
    if detail:
        # Markdown, as written. Empty for articles that live on another platform.
        data["body_th"] = a.body_th
        data["body_en"] = a.body_en
    return data


def published_articles() -> list:
    return [Article.status == "published", Article.deleted_at.is_(None)]


@router.get("/articles")
async def articles(
    limit: Annotated[int, Query(ge=1, le=60)] = 12,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
):
    where = published_articles()
    total = (await db.execute(select(func.count()).select_from(Article).where(*where))).scalar_one()
    rows = (
        await db.execute(
            select(Article)
            .where(*where)
            .order_by(Article.published_on.desc().nulls_last(), Article.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return {"total": total, "items": [article_json(a) for a in rows]}


@router.get("/articles/{article_id}")
async def article(article_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Article).where(Article.id == article_id, *published_articles()))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404)
    return article_json(row, detail=True)


@router.get("/media/{image_id}")
async def media(image_id: int, db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)):
    """An image of a public project. Drafts, hidden and trashed entries do not leak their pictures."""
    row = (
        await db.execute(
            select(ProjectImage)
            .join(Project, Project.id == ProjectImage.project_id)
            .where(ProjectImage.id == image_id, ProjectImage.deleted_at.is_(None), *visible())
        )
    ).scalar_one_or_none()
    data = await storage.get(row.key) if row else None
    if row is None or data is None:
        raise HTTPException(404)
    return image_response(data, row.content_type, "public, max-age=86400")
