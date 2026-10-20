"""What the search knows about the site's own words: a vocabulary and the glossary groups.
Kept in memory (one api process) and dropped whenever the index or the glossary changes."""
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import GlossaryEntry, Project, RagChunk, Tag
from .text import has_thai, normalize


@dataclass
class Knowledge:
    vocabulary: set[str] = field(default_factory=set)  # lower-cased Latin words used in the site's text
    groups: list[list[str]] = field(default_factory=list)  # each group: spellings of one thing


_cache: Knowledge | None = None

# Broad questions ("tell me about yourself", "how can I contact you") use words the site never writes.
# These groups tie them to the words the profile, work history and articles do use.
BUILTIN_GROUPS = [
    ["yourself", "introduce", "who are you", "about me", "แนะนำตัว", "ตัวคุณ", "เกี่ยวกับตัวคุณ", "เกี่ยวกับผม"],
    ["contact", "reach", "email", "ติดต่อ", "อีเมล"],
    ["experience", "career", "work history", "ประสบการณ์", "ประวัติการทำงาน"],
    ["location", "based", "live", "ที่อยู่", "อยู่ที่ไหน"],
    ["cv", "resume", "เรซูเม่", "ประวัติย่อ"],
    ["project", "projects", "portfolio", "ผลงาน"],
    ["article", "articles", "blog", "บทความ"],
]


def invalidate() -> None:
    global _cache
    _cache = None


def make_group(terms: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for term in terms:
        key = normalize(term, limit=None)
        if len(key) >= 2:
            seen.setdefault(key, key)
    return list(seen.values())


async def load_groups(db: AsyncSession) -> list[list[str]]:
    """Glossary entries, plus every tag with its aliases and every public project with its aliases."""
    groups = [make_group(terms) for terms in BUILTIN_GROUPS]
    groups += [
        make_group(e.terms)
        for e in (await db.execute(select(GlossaryEntry).where(GlossaryEntry.deleted_at.is_(None)))).scalars()
    ]
    for tag in (await db.execute(select(Tag).where(Tag.deleted_at.is_(None)))).scalars():
        groups.append(make_group([tag.name, *tag.aliases]))
    projects = (
        await db.execute(select(Project).where(Project.status == "published", Project.deleted_at.is_(None)))
    ).scalars()
    for project in projects:
        groups.append(make_group([project.title_th, project.title_en, *project.aliases]))
    return [g for g in groups if len(g) >= 2]


async def knowledge(db: AsyncSession) -> Knowledge:
    global _cache
    if _cache is None:
        texts = (await db.execute(select(RagChunk.search_text))).scalars().all()
        words = {w for text in texts for w in re.findall(r"[a-z]{2,}", text)}
        _cache = Knowledge(vocabulary=words, groups=await load_groups(db))
    return _cache


def match_groups(query: str, tokens: list[str], groups: list[list[str]]) -> list[list[str]]:
    """The glossary groups the question mentions. A Thai or multi-word term matches inside the text;
    a short Latin term ("pg") must be a whole word, so "xpgx" does not count."""
    present = set(tokens)
    return [
        group
        for group in groups
        if any((term in query) if (" " in term or has_thai(term)) else (term in present) for term in group)
    ]


def expand(query: str, tokens: list[str], groups: list[list[str]]) -> list[str]:
    """Other spellings of things the question mentions. "pg" brings in "postgresql"; "สต็อก" brings in "stock"."""
    present = set(tokens)
    added: dict[str, None] = {}
    for group in match_groups(query, tokens, groups):
        for term in group:
            if term not in query and term not in present:
                added[term] = None
    return list(added)
