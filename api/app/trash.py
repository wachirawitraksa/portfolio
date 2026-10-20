"""The trash: everything the owner deletes is only marked (deleted_at) and can be restored. This module
lists what is in the trash, restores it, and deletes it for good, including the files in storage."""
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Article,
    Category,
    ContactLink,
    GlossaryEntry,
    Kind,
    Project,
    ProjectImage,
    Tag,
    WorkEntry,
)
from .rag import knowledge
from .storage import Storage


@dataclass(frozen=True)
class Entry:
    label: str
    model: type
    title: Callable[[Any], str]


def _first(*parts: str) -> str:
    return next((p for p in parts if p and str(p).strip()), "")


# In the order the trash page shows them.
ENTRIES: dict[str, Entry] = {
    "project": Entry("ผลงาน / ใบเซอร์ / รายการ", Project, lambda r: _first(r.title_th, r.title_en, f"#{r.id}")),
    "image": Entry("รูปภาพ", ProjectImage, lambda r: f"รูป #{r.id} ของรายการ #{r.project_id}"),
    "work": Entry(
        "ประวัติการทำงาน", WorkEntry,
        lambda r: _first(r.position_th, r.position_en, f"#{r.id}") + (f" ({r.employer})" if r.employer else ""),
    ),
    "article": Entry("บทความ", Article, lambda r: _first(r.title_th, r.title_en, f"#{r.id}")),
    "category": Entry("ประเภท", Category, lambda r: _first(r.name_th, r.name_en, f"#{r.id}")),
    "kind": Entry("ชนิด", Kind, lambda r: _first(r.name_th, r.name_en, f"#{r.id}")),
    "tag": Entry("tag เทคโนโลยี", Tag, lambda r: r.name),
    "glossary": Entry("glossary", GlossaryEntry, lambda r: " = ".join(r.terms)),
    "link": Entry("ช่องทางติดต่อ", ContactLink, lambda r: f"{r.label} ({r.url})"),
}


async def trashed(db: AsyncSession, key: str) -> list:
    model = ENTRIES[key].model
    return list(
        (await db.execute(select(model).where(model.deleted_at.is_not(None)).order_by(model.deleted_at.desc(), model.id.desc())))
        .scalars()
    )


async def restore(db: AsyncSession, key: str, item_id: int) -> bool:
    """Bring one item back. Things that are shown to visitors come back hidden, to be looked at first."""
    from .routers.images import ensure_one_cover  # local import: the routers import this module's neighbours

    row = await db.get(ENTRIES[key].model, item_id)
    if row is None or row.deleted_at is None:
        return False
    row.deleted_at = None
    if key in ("project", "article"):
        row.status = "hidden"
    elif key == "work":
        row.hidden = True
    await db.flush()
    if key == "image":
        await ensure_one_cover(db, row.project_id)
    await db.commit()
    knowledge.invalidate()
    return True


async def purge(db: AsyncSession, storage: Storage, key: str, ids: list[int] | None = None) -> tuple[int, int]:
    """Delete trashed items for good (only items already in the trash). `ids` None means all of them.
    Returns (deleted, skipped); an item is skipped when something still depends on it."""
    model = ENTRIES[key].model
    query = select(model.id).where(model.deleted_at.is_not(None))
    if ids is not None:
        query = query.where(model.id.in_(ids))
    found = list((await db.execute(query)).scalars())
    if not found:
        return 0, 0

    # Files first: once the rows are gone nothing would remember their names.
    if key == "project":
        files = (await db.execute(select(ProjectImage.key).where(ProjectImage.project_id.in_(found)))).scalars().all()
    elif key == "image":
        files = (await db.execute(select(ProjectImage.key).where(ProjectImage.id.in_(found)))).scalars().all()
    else:
        files = []
    for file_key in files:
        await storage.delete(file_key)

    deleted = skipped = 0
    for item_id in found:
        try:
            async with db.begin_nested():
                await db.execute(delete(model).where(model.id == item_id))
            deleted += 1
        except IntegrityError:  # e.g. a kind that a project still points at
            skipped += 1
    await db.commit()
    knowledge.invalidate()
    return deleted, skipped
