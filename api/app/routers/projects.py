import re
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import current_session, require_csrf
from ..forms import is_http_url, split_lines, untranslated
from ..previews import mint, site_base
from ..models import (
    KIND_FIELD_GROUPS,
    MAX_CATEGORIES,
    PROJECT_TEXT_FIELDS,
    STATUSES,
    AuthSession,
    Category,
    Kind,
    Project,
    ProjectImage,
    Tag,
)
from ..templating import templates
from .auth import go

router = APIRouter(prefix="/projects")

# (field, label, multiline) in the order they appear in the form.
FIELDS = (
    ("title", "ชื่อ", False),
    ("problem", "โจทย์ / ทำขึ้นมาเพราะอะไร / แก้ปัญหาอะไรให้ใคร", True),
    ("work", "สิ่งที่ทำ", True),
    ("role", "บทบาทของผม (ถ้าทำกับคนอื่น)", True),
    ("result", "ผลลัพธ์ที่วัดได้ (ใส่เฉพาะตัวเลขที่ตรวจสอบได้)", True),
    ("learned", "สิ่งที่ได้เรียน / ถ้าทำใหม่จะต่างไปอย่างไร", True),
    ("next_steps", "สิ่งที่ยังอยากทำต่อ", True),
)
STATUS_LABELS = {"draft": "ร่าง", "published": "เผยแพร่", "hidden": "ถูกซ่อน"}


async def get_or_404(db: AsyncSession, project_id: int) -> Project:
    row = await db.get(Project, project_id)
    if row is None:
        raise HTTPException(404)
    return row


async def choices(db: AsyncSession):
    categories = (
        await db.execute(
            select(Category).where(Category.deleted_at.is_(None)).order_by(Category.sort_order, Category.id)
        )
    ).scalars().all()
    tags = (await db.execute(select(Tag).where(Tag.deleted_at.is_(None)).order_by(Tag.name))).scalars().all()
    kinds = (
        await db.execute(select(Kind).where(Kind.deleted_at.is_(None)).order_by(Kind.sort_order, Kind.id))
    ).scalars().all()
    return categories, tags, kinds


def filled_groups(row, tag_ids, new) -> list[str]:
    """Groups of fields this entry already has data in, so the form can say so when a kind hides them."""
    filled = []
    if any(str(getattr(row, f"{name}_{lang}", "") or "").strip() for name in PROJECT_TEXT_FIELDS[1:] for lang in ("th", "en")):
        filled.append("story")
    if tag_ids or new["tags"]:
        filled.append("tech")
    if (row.repo_url or "").strip() or (row.demo_url or "").strip():
        filled.append("links")
    if (row.issuer or "").strip() or row.issued_on or (row.verify_url or "").strip():
        filled.append("credential")
    if row.year:
        filled.append("year")
    return filled


async def form_page(request, session, db, row, category_ids, tag_ids, error=None, status=200, new=None):
    categories, tags, kinds = await choices(db)
    new = new or {"tags": [], "categories": []}
    images = trashed_images = []
    if row is not None and row.id:
        every = (
            await db.execute(
                select(ProjectImage)
                .where(ProjectImage.project_id == row.id)
                .order_by(ProjectImage.sort_order, ProjectImage.id)
            )
        ).scalars().all()
        images = [i for i in every if i.deleted_at is None]
        trashed_images = [i for i in every if i.deleted_at is not None]
    # Which groups of fields each kind shows; the page script swaps them when the kind changes.
    every_group = list(KIND_FIELD_GROUPS)
    kind_fields = {k.id: [g for g in k.fields if g in KIND_FIELD_GROUPS] for k in kinds}
    current = row.kind_id if row is not None and row.kind_id in kind_fields else (kinds[0].id if kinds else None)
    visible = kind_fields.get(current, every_group)
    context = {
        "kind_fields": kind_fields,
        "visible": visible,
        "groups": KIND_FIELD_GROUPS,
        "filled_groups": filled_groups(row, tag_ids, new) if row is not None else [],
        "images": images,
        "trashed_images": trashed_images,
        "row": row,
        "fields": FIELDS,
        "statuses": [(s, STATUS_LABELS[s]) for s in STATUSES],
        "kinds": kinds,
        "categories": categories,
        "tags": tags,
        # Chips already on the card: value is an id, or the typed name when new.
        "chosen_categories": [
            {"value": c.id, "label": c.name_th or c.name_en, "new": False} for c in categories if c.id in category_ids
        ]
        + [{"value": n, "label": n, "new": True} for n in new["categories"]],
        "chosen_tags": [{"value": t.id, "label": t.name, "new": False} for t in tags if t.id in tag_ids]
        + [{"value": n, "label": n, "new": True} for n in new["tags"]],
        # One option per item. "label" is what the list shows; "names" are all the
        # spellings a typed name may match (Thai and English name, tag aliases).
        "category_options": [
            {"id": c.id, "label": c.name_th or c.name_en, "also": c.name_en if c.name_th else "",
             "names": [n for n in (c.name_th, c.name_en) if n]}
            for c in categories
        ],
        "tag_options": [
            {"id": t.id, "label": t.name, "also": ", ".join(t.aliases), "names": [t.name, *t.aliases]} for t in tags
        ],
        "max_categories": MAX_CATEGORIES,
        "error": error,
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "project_form.html", context, status_code=status)


def read_form(form) -> tuple[dict, list[int], list[int], dict, str | None]:
    """Values from the submitted form, plus the first problem found (or None)."""
    values: dict = {}
    for name in PROJECT_TEXT_FIELDS:
        for lang in ("th", "en"):
            values[f"{name}_{lang}"] = str(form.get(f"{name}_{lang}", "")).strip()
    values["repo_url"] = str(form.get("repo_url", "")).strip()
    values["demo_url"] = str(form.get("demo_url", "")).strip()
    values["aliases"] = split_lines(str(form.get("aliases", "")))
    values["status"] = str(form.get("status", "draft"))
    values["featured"] = form.get("featured") is not None
    values["issuer"] = str(form.get("issuer", "")).strip()
    values["verify_url"] = str(form.get("verify_url", "")).strip()
    kind_id = str(form.get("kind_id", "")).strip()
    values["kind_id"] = int(kind_id) if kind_id.isdigit() else None

    error = None
    year = str(form.get("year", "")).strip()
    values["year"] = None
    if year:
        if year.isdigit() and 1990 <= int(year) <= 2100:
            values["year"] = int(year)
        else:
            error = "ปีต้องเป็นตัวเลข เช่น 2025"
    issued_on = str(form.get("issued_on", "")).strip()
    values["issued_on"] = None
    if issued_on:
        try:
            values["issued_on"] = date.fromisoformat(issued_on)
        except ValueError:
            error = error or "วันที่ไม่ถูกต้อง"
    if values["status"] not in STATUSES:
        error = error or "สถานะไม่ถูกต้อง"
    for key, label in (("repo_url", "ลิงก์ repo"), ("demo_url", "ลิงก์ demo"), ("verify_url", "ลิงก์ตรวจสอบ")):
        if values[key] and not is_http_url(values[key]):
            error = error or f"{label}ต้องขึ้นต้นด้วย http:// หรือ https://"
    if not (values["title_th"] or values["title_en"]):
        error = error or "ต้องกรอกชื่ออย่างน้อยหนึ่งภาษา"

    def ids(key: str) -> list[int]:
        return sorted({int(v) for v in form.getlist(key) if str(v).isdigit()})

    def names(key: str) -> list[str]:
        return split_lines("\n".join(str(v).replace("\n", " ") for v in form.getlist(key)))

    new = {"tags": names("new_tags"), "categories": names("new_categories")}
    return values, ids("category_ids"), ids("tag_ids"), new, error


THAI = re.compile("[\u0e00-\u0e7f]")


async def resolve_tags(db: AsyncSession, ids: list[int], names: list[str]) -> tuple[list[Tag], list[str]]:
    """Tags for the ids, plus tags whose name or alias matches a typed name.
    Returns (tags found, typed names that need a new tag)."""
    found = {
        t.id: t for t in (await db.execute(select(Tag).where(Tag.id.in_(ids), Tag.deleted_at.is_(None)))).scalars()
    }
    missing = []
    everything = (await db.execute(select(Tag))).scalars().all()
    for name in names:
        key = name.lower()
        match = next((t for t in everything if t.name.lower() == key or key in (a.lower() for a in t.aliases)), None)
        if match is None:
            missing.append(name)
        else:
            found[match.id] = match
    return list(found.values()), missing


async def resolve_categories(db: AsyncSession, ids: list[int], names: list[str]) -> tuple[list[Category], list[str]]:
    found = {
        c.id: c
        for c in (
            await db.execute(select(Category).where(Category.id.in_(ids), Category.deleted_at.is_(None)))
        ).scalars()
    }
    missing = []
    live = (await db.execute(select(Category).where(Category.deleted_at.is_(None)))).scalars().all()
    for name in names:
        key = name.lower()
        match = next((c for c in live if key in (c.name_th.lower(), c.name_en.lower())), None)
        if match is None:
            missing.append(name)
        else:
            found[match.id] = match
    return list(found.values()), missing


async def save(request, session, db, row: Project | None):
    values, category_ids, tag_ids, new, error = read_form(await request.form())
    # Look these up before the new row joins the session; a query autoflushes it,
    # and assigning a relationship afterwards would load the old value (async IO).
    categories, new_categories = await resolve_categories(db, category_ids, new["categories"])
    tags, new_tags = await resolve_tags(db, tag_ids, new["tags"])
    if not error and len(categories) + len(new_categories) > MAX_CATEGORIES:
        error = f"เลือกประเภทได้ไม่เกิน {MAX_CATEGORIES} ประเภท"
    if not error and values["kind_id"] is not None:
        kind = await db.get(Kind, values["kind_id"])
        if kind is None or kind.deleted_at is not None:
            error = "ไม่พบชนิดที่เลือก"
    if error:
        kept_categories = [c.id for c in categories]
        kept_tags = [t.id for t in tags]
        shown = Project(id=row.id if row else None, **values)
        return await form_page(
            request,
            session,
            db,
            shown,
            kept_categories,
            kept_tags,
            error,
            422,
            {"tags": new_tags, "categories": new_categories},
        )
    for tag in tags:
        tag.deleted_at = None  # typing a trashed tag's name brings it back
    last_category = (await db.execute(select(func.coalesce(func.max(Category.sort_order), 0)))).scalar_one()
    for offset, name in enumerate(new_categories, start=1):
        # A new category takes the name in the language it was typed in; the other stays empty.
        field = {"name_th": name} if THAI.search(name) else {"name_en": name}
        category = Category(sort_order=last_category + offset, hidden=False, **field)
        db.add(category)
        categories.append(category)
    for name in new_tags:
        tag = Tag(name=name, aliases=[])
        db.add(tag)
        tags.append(tag)
    if row is None:
        last = (await db.execute(select(func.coalesce(func.max(Project.sort_order), 0)))).scalar_one()
        db.add(Project(sort_order=last + 1, categories=categories, tags=tags, **values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
        row.categories, row.tags = categories, tags
    await db.commit()
    return go("/projects")


@router.get("", response_class=HTMLResponse)
async def list_projects(
    request: Request,
    trash: bool = False,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).order_by(Project.sort_order, Project.id)
    query = query.where(Project.deleted_at.is_not(None) if trash else Project.deleted_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    context = {
        "rows": rows,
        "trash": trash,
        "status_labels": STATUS_LABELS,
        "untranslated": {r.id: untranslated(r) for r in rows},
        "csrf": session.csrf_token,
    }
    return templates.TemplateResponse(request, "projects.html", context)


@router.get("/new", response_class=HTMLResponse)
async def new_form(
    request: Request, session: AuthSession = Depends(current_session), db: AsyncSession = Depends(get_db)
):
    return await form_page(request, session, db, None, [], [])


@router.post("")
async def create(
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    return await save(request, session, db, None)


@router.get("/{project_id}/edit", response_class=HTMLResponse)
async def edit_form(
    project_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    row = await get_or_404(db, project_id)
    return await form_page(request, session, db, row, [c.id for c in row.categories], [t.id for t in row.tags])


@router.get("/{project_id}/preview")
async def preview(
    project_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
):
    """Open this entry on the real website, drafts included. The link works for a few minutes."""
    row = await get_or_404(db, project_id)
    token = await mint(db, "project", row.id)
    lang = "en" if request.cookies.get("lang") == "en" else "th"
    return RedirectResponse(f"{site_base(request)}/{lang}/projects/{row.id}?preview={token}", status_code=302)


@router.post("/{project_id}")
async def update(
    project_id: int,
    request: Request,
    session: AuthSession = Depends(current_session),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    return await save(request, session, db, await get_or_404(db, project_id))


@router.post("/{project_id}/feature")
async def toggle_featured(
    project_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)
):
    row = await get_or_404(db, project_id)
    row.featured = not row.featured
    await db.commit()
    return go("/projects")


@router.post("/{project_id}/move")
async def move(
    project_id: int,
    direction: str = Form(...),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Project).where(Project.deleted_at.is_(None)).order_by(Project.sort_order, Project.id)
        )
    ).scalars().all()
    index = next((i for i, r in enumerate(rows) if r.id == project_id), None)
    if index is None:
        raise HTTPException(404)
    swap = index - 1 if direction == "up" else index + 1
    if 0 <= swap < len(rows):
        rows[index], rows[swap] = rows[swap], rows[index]
    for position, row in enumerate(rows, start=1):
        row.sort_order = position
    await db.commit()
    return go("/projects")


@router.post("/{project_id}/trash")
async def trash(project_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, project_id)
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return go("/projects")


@router.post("/{project_id}/restore")
async def restore(project_id: int, _: None = Depends(require_csrf), db: AsyncSession = Depends(get_db)):
    row = await get_or_404(db, project_id)
    row.deleted_at = None
    row.status = "hidden"  # comes back hidden, so it is reviewed before it shows again
    await db.commit()
    return go("/projects?trash=true")
