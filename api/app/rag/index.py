"""Turn the site's published content into searchable chunks. Run by the "rebuild" button."""
from contextvars import ContextVar
from itertools import zip_longest

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    EDUCATION_LEVELS,
    EMPLOYMENT_TYPES,
    Article,
    ContactLink,
    EducationEntry,
    Project,
    RagChunk,
    WorkEntry,
)
from ..site import get_profile
from ..visibility import project_visible
from . import knowledge
from .embed import embed
from .text import normalize, sound_key, tokenize

PARAGRAPH_LIMIT = 1000  # letters in one article chunk

# Words that name the kind of thing a chunk is, so "what projects do you have" finds the projects
# even though no project writes the word "project".
TYPE_WORDS = {
    "project": ["project", "projects", "portfolio", "ผลงาน"],
    "work": ["work", "experience", "job", "career", "ประสบการณ์", "ประวัติการทำงาน", "ที่ทำงาน"],
    "education": ["education", "study", "degree", "university", "school", "ประวัติการศึกษา", "การศึกษา", "มหาวิทยาลัย", "ปริญญา"],
    "article": ["article", "articles", "blog", "บทความ"],
    "profile": ["about me", "profile", "contact", "ติดต่อ", "เกี่ยวกับผม", "location", "ที่อยู่"],
}


def lines(*items: tuple[str, str]) -> str:
    """"label: value" lines, leaving out the empty ones."""
    return "\n".join(f"{label}: {value}" if label else value for label, value in items if str(value).strip())


# While comparing the index with the content (index_status) the slow parts, word cutting, phonetic keys and
# vectors, are skipped: the text itself is enough to tell whether something changed.
_comparing: ContextVar[bool] = ContextVar("rag_comparing", default=False)


def make_chunk(source_type, source_id, section, title_th, title_en, body_th, body_en, extra=()) -> RagChunk:
    search_text = normalize(" ".join([title_th, title_en, body_th, body_en, *extra, *TYPE_WORDS[source_type]]), limit=None)
    if _comparing.get():
        return RagChunk(
            source_type=source_type, source_id=source_id, section=section, title_th=title_th, title_en=title_en,
            body_th=body_th, body_en=body_en, search_text=search_text, sound="", embedding=[],
        )
    tokens = tokenize(search_text)
    return RagChunk(
        source_type=source_type,
        source_id=source_id,
        section=section,
        title_th=title_th,
        title_en=title_en,
        body_th=body_th,
        body_en=body_en,
        search_text=search_text,
        sound=sound_key(list(dict.fromkeys(tokens))),
        embedding=embed(search_text, tokens),
    )


def project_chunks(p: Project) -> list[RagChunk]:
    tags = [t for t in p.tags if t.deleted_at is None]
    categories = [c for c in p.categories if c.deleted_at is None and not c.hidden]
    # Everything that names this project finds all of its chunks, not only the first.
    extra = [*p.aliases, *(t.name for t in tags), *(a for t in tags for a in t.aliases)]
    tag_names = ", ".join(t.name for t in tags)
    category_th = ", ".join(c.name_th or c.name_en for c in categories)
    category_en = ", ".join(c.name_en or c.name_th for c in categories)
    kind = p.kind if p.kind and not p.kind.hidden and p.kind.deleted_at is None else None
    links = (("Repo", p.repo_url), ("Demo", p.demo_url), ("ลิงก์ตรวจสอบ / Verify", p.verify_url))

    chunks = [
        make_chunk(
            "project", p.id, "overview", p.title_th, p.title_en,
            lines(
                ("ชนิด", kind.name_th if kind else ""), ("ปี", p.year or ""), ("ประเภท", category_th),
                ("โจทย์", p.problem_th), ("บทบาท", p.role_th), ("ผู้ออก", p.issuer),
                ("เทคโนโลยี", tag_names), *links,
            ),
            lines(
                ("Kind", kind.name_en if kind else ""), ("Year", p.year or ""), ("Categories", category_en),
                ("Problem", p.problem_en), ("Role", p.role_en), ("Issuer", p.issuer),
                ("Technologies", tag_names), *links,
            ),
            extra,
        )
    ]
    for section, label_th, label_en in (
        ("work", "สิ่งที่ทำ", "What I did"),
        ("result", "ผลลัพธ์", "Result"),
        ("learned", "สิ่งที่ได้เรียน", "What I learned"),
        ("next_steps", "สิ่งที่อยากทำต่อ", "What is next"),
    ):
        text_th, text_en = getattr(p, f"{section}_th"), getattr(p, f"{section}_en")
        if text_th.strip() or text_en.strip():
            chunks.append(
                make_chunk(
                    "project", p.id, section, p.title_th, p.title_en,
                    lines((label_th, text_th)), lines((label_en, text_en)), extra,
                )
            )
    return chunks


def work_chunk(w: WorkEntry) -> RagChunk:
    tags = [t for t in w.tags if t.deleted_at is None]
    extra = [w.employer, *(t.name for t in tags), *(a for t in tags for a in t.aliases)]
    period = w.started_on.isoformat() + (
        " – ปัจจุบัน / present" if w.span == "ongoing" else "" if w.span == "moment" else f" – {w.ended_on.isoformat()}"
    )
    type_th, type_en = EMPLOYMENT_TYPES[w.employment_type]
    tag_names = ", ".join(t.name for t in tags)
    bullets_th = "\n".join(f"• {b}" for b in w.bullets_th.splitlines())
    bullets_en = "\n".join(f"• {b}" for b in w.bullets_en.splitlines())
    return make_chunk(
        "work", w.id, "job",
        f"{w.position_th} ({w.employer})" if w.employer else w.position_th,
        f"{w.position_en} ({w.employer})" if w.employer else w.position_en,
        lines(("ช่วงเวลา", period), ("รูปแบบ", type_th), ("เครื่องมือ", tag_names), ("", bullets_th)),
        lines(("Period", period), ("Type", type_en), ("Tools", tag_names), ("", bullets_en)),
        extra,
    )


def education_chunk(e: EducationEntry) -> RagChunk:
    level_th, level_en = EDUCATION_LEVELS[e.level]
    period = e.started_on.strftime("%Y-%m") + (" – ปัจจุบัน / present" if e.ongoing else f" – {e.ended_on.strftime('%Y-%m')}")
    items_th = "\n".join(f"• {d}" for d in e.details_th.splitlines())
    items_en = "\n".join(f"• {d}" for d in e.details_en.splitlines())

    def title(institution: str, degree: str, field: str) -> str:
        head = " ".join(part for part in (degree, field) if part)
        return f"{head} ({institution})" if head and institution else head or institution

    return make_chunk(
        "education", e.id, "school",
        title(e.institution_th, e.degree_th, e.field_th), title(e.institution_en, e.degree_en, e.field_en),
        lines(("สถาบัน", e.institution_th), ("ระดับ", level_th), ("วุฒิ", e.degree_th), ("สาขา", e.field_th),
              ("ช่วงเวลา", period), ("เกรด", e.grade), ("", items_th)),
        lines(("Institution", e.institution_en), ("Level", level_en), ("Degree", e.degree_en), ("Field", e.field_en),
              ("Period", period), ("Grade", e.grade), ("", items_en)),
        [e.institution_th, e.institution_en],
    )


def paragraph_groups(text: str) -> list[str]:
    """Paragraphs packed into groups of at most PARAGRAPH_LIMIT letters (a long paragraph stays whole)."""
    groups: list[str] = []
    current = ""
    for paragraph in (p.strip() for p in text.split("\n\n")):
        if not paragraph:
            continue
        if current and len(current) + len(paragraph) > PARAGRAPH_LIMIT:
            groups.append(current)
            current = ""
        current = f"{current}\n\n{paragraph}" if current else paragraph
    return groups + ([current] if current else [])


def article_chunks(a: Article) -> list[RagChunk]:
    extra = [t.name for t in a.tags if t.deleted_at is None]
    where = ("Platform", a.platform), ("Link", a.external_url)
    chunks = [
        make_chunk(
            "article", a.id, "summary", a.title_th, a.title_en,
            lines(("สรุป", a.summary_th), *where), lines(("Summary", a.summary_en), *where), extra,
        )
    ]
    for number, (th, en) in enumerate(
        zip_longest(paragraph_groups(a.body_th), paragraph_groups(a.body_en), fillvalue=""), start=1
    ):
        chunks.append(make_chunk("article", a.id, f"body{number}", a.title_th, a.title_en, th, en, extra))
    return chunks


async def profile_chunk(db: AsyncSession) -> RagChunk | None:
    p = await get_profile(db)
    links = (
        await db.execute(select(ContactLink).where(ContactLink.deleted_at.is_(None)).order_by(ContactLink.sort_order))
    ).scalars().all()
    link_lines = [(link.label, link.url) for link in links]
    cv = [label for label, key in (("ไทย", p.cv_th_key), ("English", p.cv_en_key)) if key]
    if not (p.name_th or p.name_en or p.intro_th or p.intro_en):
        return None
    return make_chunk(
        "profile", 1, "about", "เกี่ยวกับผม", "About me",
        lines(("ชื่อ", p.name_th), ("ตำแหน่ง", p.headline_th), ("แนะนำตัว", p.intro_th), ("ที่อยู่", p.location_th), ("อีเมล", p.email),
              *link_lines, ("CV ดาวน์โหลดได้", ", ".join(cv))),
        lines(("Name", p.name_en), ("Headline", p.headline_en), ("About", p.intro_en), ("Location", p.location_en), ("Email", p.email),
              *link_lines, ("CV available", ", ".join(cv))),
    )


async def collect(db: AsyncSession) -> list[RagChunk]:
    """The chunks today's public content produces, not yet stored."""
    chunks: list[RagChunk] = []
    projects = (
        await db.execute(
            select(Project).where(*project_visible()).order_by(Project.id)
        )
    ).scalars()
    for project in projects:
        chunks.extend(project_chunks(project))
    work = (
        await db.execute(
            select(WorkEntry).where(WorkEntry.hidden.is_(False), WorkEntry.deleted_at.is_(None)).order_by(WorkEntry.id)
        )
    ).scalars()
    chunks.extend(work_chunk(w) for w in work)
    schools = (
        await db.execute(
            select(EducationEntry)
            .where(EducationEntry.hidden.is_(False), EducationEntry.deleted_at.is_(None))
            .order_by(EducationEntry.id)
        )
    ).scalars()
    chunks.extend(education_chunk(e) for e in schools)
    articles = (
        await db.execute(select(Article).where(Article.status == "published", Article.deleted_at.is_(None)).order_by(Article.id))
    ).scalars()
    for article in articles:
        chunks.extend(article_chunks(article))
    if (about := await profile_chunk(db)) is not None:
        chunks.append(about)
    return chunks


def content_of(chunk: RagChunk) -> tuple:
    return (chunk.title_th, chunk.title_en, chunk.body_th, chunk.body_en, chunk.search_text)


async def index_status(db: AsyncSession) -> dict:
    """Has the content changed since the last rebuild? Compares what is stored with what the content
    would produce now. `stale` is True when anything was added, edited or removed."""
    token = _comparing.set(True)
    try:
        fresh = {(c.source_type, c.source_id, c.section): content_of(c) for c in await collect(db)}
    finally:
        _comparing.reset(token)
    stored = {
        (c.source_type, c.source_id, c.section): content_of(c)
        for c in (await db.execute(select(RagChunk))).scalars()
    }
    added = len(fresh.keys() - stored.keys())
    removed = len(stored.keys() - fresh.keys())
    changed = sum(1 for key in fresh.keys() & stored.keys() if fresh[key] != stored[key])
    return {"stale": bool(added or removed or changed), "added": added, "removed": removed, "changed": changed,
            "built": bool(stored)}


async def rebuild(db: AsyncSession) -> dict[str, int]:
    """Replace every chunk with ones built from today's content. Returns the chunk count per source type."""
    chunks = await collect(db)
    await db.execute(delete(RagChunk))
    db.add_all(chunks)
    await db.commit()
    knowledge.invalidate()
    counts: dict[str, int] = {}
    for chunk in chunks:
        counts[chunk.source_type] = counts.get(chunk.source_type, 0) + 1
    return counts
