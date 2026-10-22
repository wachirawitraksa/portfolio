from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import (
    EDUCATION_LEVELS,
    EMPLOYMENT_TYPES,
    PROJECT_TEXT_FIELDS,
    Article,
    Category,
    ContactLink,
    EducationEntry,
    Kind,
    Project,
    ProjectImage,
    Tag,
    WorkEntry,
    project_category,
    project_tag,
)
from ..schemas import (
    ArticleDetail,
    ArticleList,
    CategoryOut,
    EducationItem,
    KindOut,
    ProfileOut,
    ProjectDetail,
    ProjectList,
    ProjectCard,
    SettingsOut,
    TagCount,
    UpdateItem,
    WorkItem,
)
from ..imaging import variant, width_param
from ..previews import valid as preview_valid
from ..site import get_profile, get_site_settings
from ..visibility import project_visible
from ..storage import Storage, get_storage
from .images import image_response
from .profile import file_response, version

router = APIRouter()

# Only the fields a card needs. The detail view returns every text field.
CARD_TEXT_FIELDS = ("title", "problem")


def visible() -> list:
    return project_visible()


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


@router.get("/categories", response_model=list[CategoryOut])
async def categories(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Category)
            .where(Category.hidden.is_(False), Category.deleted_at.is_(None))
            .order_by(Category.sort_order, Category.id)
        )
    ).scalars().all()
    return [{"id": r.id, "name_th": r.name_th, "name_en": r.name_en} for r in rows]


@router.get("/kinds", response_model=list[KindOut])
async def kinds(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Kind)
            .where(Kind.hidden.is_(False), Kind.deleted_at.is_(None))
            .order_by(Kind.sort_order, Kind.id)
        )
    ).scalars().all()
    return [{"id": r.id, "name_th": r.name_th, "name_en": r.name_en} for r in rows]


@router.get("/tags", response_model=list[TagCount])
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
    return [{"id": tag.id, "name": tag.name, "count": n, "group_th": tag.group_th, "group_en": tag.group_en} for tag, n in rows]


@router.get("/projects", response_model=ProjectList)
async def projects(
    q: Annotated[str, Query(max_length=100)] = "",
    tag: Annotated[list[int], Query()] = [],
    category: int | None = None,
    kind: int | None = None,
    sort: Literal["order", "newest", "oldest"] = "order",
    limit: Annotated[int | None, Query(ge=1, le=60)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
):
    """Public project list. Every tag given must match (narrowing, not widening).
    Without `limit`, the page size set in the admin applies."""
    limit = limit or (await get_site_settings(db)).projects_page_size
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


@router.get("/projects/featured", response_model=list[ProjectCard])
async def featured(limit: Annotated[int | None, Query(ge=1, le=60)] = None, db: AsyncSession = Depends(get_db)):
    limit = limit or (await get_site_settings(db)).featured_limit
    rows = (
        await db.execute(
            select(Project)
            .where(*visible(), Project.featured.is_(True))
            .order_by(Project.sort_order, Project.id)
            .limit(limit)
        )
    ).scalars().all()
    return [project_json(p, CARD_TEXT_FIELDS) for p in rows]


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def project(project_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Project).where(Project.id == project_id, *visible()))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404)
    return project_json(row, PROJECT_TEXT_FIELDS, detail=True)


@router.get("/how-i-work", response_model=ProjectDetail | None)
async def how_i_work(db: AsyncSession = Depends(get_db)):
    """The project chosen in the admin to tell the "how I work" story, or null when none is chosen
    (or the chosen one is not published), so the website simply leaves that section out."""
    project_id = (await get_site_settings(db)).how_i_work_project_id
    if project_id is None:
        return None
    row = (await db.execute(select(Project).where(Project.id == project_id, *visible()))).scalar_one_or_none()
    return project_json(row, PROJECT_TEXT_FIELDS, detail=True) if row else None


@router.get("/experience", response_model=list[WorkItem])
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


@router.get("/education", response_model=list[EducationItem])
async def education(db: AsyncSession = Depends(get_db)):
    """Schools and degrees, newest first. Hidden and trashed entries stay out."""
    rows = (
        await db.execute(
            select(EducationEntry)
            .where(EducationEntry.hidden.is_(False), EducationEntry.deleted_at.is_(None))
            .order_by(EducationEntry.started_on.desc(), EducationEntry.id.desc())
        )
    ).scalars().all()
    return [
        {
            "id": e.id,
            "institution_th": e.institution_th,
            "institution_en": e.institution_en,
            "level": e.level,
            "level_th": EDUCATION_LEVELS[e.level][0],
            "level_en": EDUCATION_LEVELS[e.level][1],
            "degree_th": e.degree_th,
            "degree_en": e.degree_en,
            "field_th": e.field_th,
            "field_en": e.field_en,
            "grade": e.grade,
            "span": e.span,
            "started_on": e.started_on.strftime("%Y-%m"),
            "ended_on": None if e.ongoing else e.ended_on.strftime("%Y-%m"),
            "details_th": e.details_th.splitlines(),
            "details_en": e.details_en.splitlines(),
        }
        for e in rows
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


@router.get("/articles", response_model=ArticleList)
async def articles(
    limit: Annotated[int | None, Query(ge=1, le=60)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
):
    limit = limit or (await get_site_settings(db)).articles_page_size
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


@router.get("/articles/{article_id}", response_model=ArticleDetail)
async def article(article_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Article).where(Article.id == article_id, *published_articles()))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404)
    return article_json(row, detail=True)


@router.get("/profile", response_model=ProfileOut)
async def profile(db: AsyncSession = Depends(get_db)):
    """Home page details. A missing photo or CV is null, never a broken URL."""
    p = await get_profile(db)
    contact_links = (
        await db.execute(
            select(ContactLink).where(ContactLink.deleted_at.is_(None)).order_by(ContactLink.sort_order, ContactLink.id)
        )
    ).scalars().all()
    return {
        "name_th": p.name_th,
        "name_en": p.name_en,
        "intro_th": p.intro_th,
        "intro_en": p.intro_en,
        "location_th": p.location_th,
        "location_en": p.location_en,
        "headline_th": p.headline_th,
        "headline_en": p.headline_en,
        "email": p.email,
        "photo_url": f"/api/profile/photo?v={version(p.photo_key)}" if p.photo_key else None,
        "cv_th_url": f"/api/profile/cv/th?v={version(p.cv_th_key)}" if p.cv_th_key else None,
        "cv_en_url": f"/api/profile/cv/en?v={version(p.cv_en_key)}" if p.cv_en_key else None,
        "links": [{"id": link.id, "label": link.label, "url": link.url} for link in contact_links],
    }


@router.get("/profile/photo")
async def profile_photo(
    w: int | None = Depends(width_param), db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)
):
    p = await get_profile(db)
    if not p.photo_key:
        raise HTTPException(404)
    # The URL carries a version tag that changes with the file, so it may be cached for good.
    cache = "public, max-age=31536000, immutable"
    if w and (made := await variant(storage, p.photo_key, w)):
        return file_response(made[0], made[1], cache)
    data = await storage.get(p.photo_key)
    if data is None:
        raise HTTPException(404)
    return file_response(data, p.photo_content_type, cache)


@router.get("/profile/cv/{lang}")
async def profile_cv(lang: str, db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)):
    if lang not in ("th", "en"):
        raise HTTPException(404)
    p = await get_profile(db)
    key = getattr(p, f"cv_{lang}_key")
    data = await storage.get(key) if key else None
    if data is None:
        raise HTTPException(404)
    return file_response(data, "application/pdf", "public, max-age=31536000, immutable", f"cv-{lang}.pdf")


@router.get("/settings", response_model=SettingsOut)
async def site_settings(db: AsyncSession = Depends(get_db)):
    s = await get_site_settings(db)
    return {
        "featured_limit": s.featured_limit,
        "projects_page_size": s.projects_page_size,
        "articles_page_size": s.articles_page_size,
        "how_i_work_project_id": s.how_i_work_project_id,
        "site_title_th": s.site_title_th,
        "site_title_en": s.site_title_en,
        "site_description_th": s.site_description_th,
        "site_description_en": s.site_description_en,
    }


@router.get("/media/{image_id}")
async def media(
    image_id: int,
    w: int | None = Depends(width_param),
    preview: str | None = None,
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    """An image of a public project, optionally at one of the fixed widths (`?w=480`).
    Drafts, hidden and trashed entries do not leak their pictures, unless a valid preview link names the project."""
    row = (
        await db.execute(
            select(ProjectImage)
            .join(Project, Project.id == ProjectImage.project_id)
            .where(ProjectImage.id == image_id, ProjectImage.deleted_at.is_(None), *visible())
        )
    ).scalar_one_or_none()
    cache = "public, max-age=86400"
    if row is None and preview:
        candidate = await db.get(ProjectImage, image_id)
        if candidate and candidate.deleted_at is None and await preview_valid(db, preview, "project", candidate.project_id):
            row, cache = candidate, "private, no-store"
    if row is None:
        raise HTTPException(404)
    if w and (made := await variant(storage, row.key, w)):
        return image_response(made[0], made[1], cache)
    data = await storage.get(row.key)
    if data is None:
        raise HTTPException(404)
    return image_response(data, row.content_type, cache)


def no_index(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex"


@router.get("/preview/projects/{project_id}", response_model=ProjectDetail)
async def preview_project(project_id: int, token: str, response: Response, db: AsyncSession = Depends(get_db)):
    """A project as it will look once published, for the owner's preview link only (drafts included)."""
    row = await db.get(Project, project_id)
    if row is None or row.deleted_at is not None or not await preview_valid(db, token, "project", project_id):
        raise HTTPException(404)
    no_index(response)
    return project_json(row, PROJECT_TEXT_FIELDS, detail=True)


@router.get("/preview/articles/{article_id}", response_model=ArticleDetail)
async def preview_article(article_id: int, token: str, response: Response, db: AsyncSession = Depends(get_db)):
    row = await db.get(Article, article_id)
    if row is None or row.deleted_at is not None or not await preview_valid(db, token, "article", article_id):
        raise HTTPException(404)
    no_index(response)
    return article_json(row, detail=True)


@router.get("/updates", response_model=list[UpdateItem])
async def updates(limit: Annotated[int, Query(ge=1, le=30)] = 8, db: AsyncSession = Depends(get_db)):
    """What was edited lately, newest first: public projects and articles, work and education that are not hidden,
    and the profile. Entries that have not been edited since the site started recording it are left out
    rather than given a made-up date."""

    def newest(model, *where):
        return select(model).where(model.updated_at.is_not(None), *where).order_by(model.updated_at.desc()).limit(limit)

    found: list[tuple] = []
    for p in (await db.execute(newest(Project, *visible()))).scalars():
        kind = {"id": p.kind.id, "name_th": p.kind.name_th, "name_en": p.kind.name_en} if p.kind else None
        found.append((p.updated_at, "project", p.id, p.title_th, p.title_en, kind))
    for a in (await db.execute(newest(Article, *published_articles()))).scalars():
        found.append((a.updated_at, "article", a.id, a.title_th, a.title_en, None))
    for w in (await db.execute(newest(WorkEntry, WorkEntry.hidden.is_(False), WorkEntry.deleted_at.is_(None)))).scalars():
        found.append((w.updated_at, "work", w.id, w.position_th, w.position_en, None))
    for e in (
        await db.execute(newest(EducationEntry, EducationEntry.hidden.is_(False), EducationEntry.deleted_at.is_(None)))
    ).scalars():
        found.append((e.updated_at, "education", e.id, e.institution_th, e.institution_en, None))
    me = await get_profile(db)
    if me.updated_at and (me.name_th or me.name_en or me.intro_th or me.intro_en):
        found.append((me.updated_at, "profile", me.id, me.name_th, me.name_en, None))
    found.sort(key=lambda row: row[0], reverse=True)
    return [
        {"type": kind_of, "id": item_id, "title_th": th, "title_en": en, "kind": kind, "at": at.isoformat()}
        for at, kind_of, item_id, th, en, kind in found[:limit]
    ]
