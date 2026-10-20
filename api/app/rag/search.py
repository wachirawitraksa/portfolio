"""Find the site text that answers a question. No model is called here.

Every candidate chunk is scored on four signals, all computed in the database:
  keyword   how much of the question the chunk covers. The question is split into concepts: a word, or a
            glossary group of spellings (pg / postgres / postgresql). A concept counts fully when one of its
            spellings appears, partly when a spelling is close (typo, pg_trgm), and partly when its sound
            matches (Thai typed in Latin letters). Longer words weigh more than short ones.
  trigram   pg_trgm word similarity of the whole question
  vector    cosine similarity of the hashed embedding (rag/embed.py)
  sound     pg_trgm on a phonetic key of the Latin words the site does not use
The signals are blended, lightly re-ranked, and turned into a confidence band that decides whether, and
how cheaply, a model is asked to write the answer."""
import re
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import Float, case, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RagChunk
from .embed import embed
from .knowledge import Knowledge, expand, knowledge, match_groups
from .text import (
    COMMON_ENGLISH,
    MAX_QUESTION_CHARS,
    SPACES,
    STOPWORDS,
    content_tokens,
    fix_keyboard,
    has_thai,
    language_of,
    normalize,
    skeleton,
    sound_key,
    tokenize,
)

# How much each signal counts in the blend.
W_KEYWORD, W_VECTOR, W_TRIGRAM, W_SOUND = 0.55, 0.25, 0.12, 0.08
# Cosine similarity of unrelated hashed text sits near 0.1; related text reaches about 0.5.
VECTOR_FLOOR, VECTOR_SPAN = 0.1, 0.4
TITLE_BOOST = PHRASE_BOOST = 0.08

FUZZY_MIN_LETTERS = 4  # shorter words are too easy to confuse
FUZZY_SIMILARITY = 0.6  # pg_trgm word similarity that counts as "the same word, misspelled"
FUZZY_CREDIT = 0.8
SOUND_CREDIT = 0.9
SOUND_MIN_LETTERS = 3
MAX_WEIGHT = 6  # a long word weighs more than a short one, up to this many letters

HIGH, MEDIUM = 0.5, 0.25  # score needed for each confidence band
MIN_HIT = 0.2  # chunks scoring below this are not shown at all
CANDIDATES = 40
MAX_HITS = 5
MAX_PER_SOURCE = 2  # chunks of one project/job/article in the answer context


@dataclass
class Concept:
    """One thing the question asks about, with every way the site might write it."""

    terms: list[str]
    sounds: list[str] = field(default_factory=list)  # phonetic keys, for Latin words that may be Thai
    weight: int = 1


@dataclass
class Prepared:
    raw: str
    text: str  # normalized, keyboard fixed
    keyboard_fixed: bool
    language: str
    tokens: list[str]
    concepts: list[Concept]
    expansions: list[str]  # spellings added from the glossary
    sound: str  # phonetic key of Latin words the site does not use; empty when there are none


@dataclass
class Hit:
    chunk: RagChunk
    score: float
    keyword: float
    vector: float
    trigram: float
    sound: float


@dataclass
class Retrieval:
    prepared: Prepared
    hits: list[Hit] = field(default_factory=list)
    band: str = "low"  # high | medium | low

    @property
    def top(self) -> float:
        return self.hits[0].score if self.hits else 0.0


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def weight_of(terms: list[str]) -> int:
    return max(1, min(max(len(t) for t in terms), MAX_WEIGHT))


def prepare(raw: str, kn: Knowledge) -> Prepared:
    cleaned = SPACES.sub(" ", unicodedata.normalize("NFKC", raw)).strip()[: MAX_QUESTION_CHARS * 2]
    fixed, changed = fix_keyboard(cleaned, kn.vocabulary)
    text = normalize(fixed)
    tokens = tokenize(text)
    content = content_tokens(tokens)
    matched = match_groups(text, tokens, kn.groups)
    consumed = {t for t in content if any(t == term or (len(t) >= 2 and t in term) for g in matched for term in g)}
    # Latin words the site never uses may be Thai typed in Latin letters.
    unknown = [
        t
        for t in tokens
        if re.fullmatch(r"[a-z]{2,}", t) and t not in kn.vocabulary and t not in COMMON_ENGLISH and t not in STOPWORDS
    ]
    concepts = [Concept(list(g), weight=weight_of(g)) for g in matched]
    for token in content:
        if token in consumed:
            continue
        key = skeleton(token)
        sounds = [key] if token in unknown and len(key) >= SOUND_MIN_LETTERS else []
        concepts.append(Concept([token], sounds, weight_of([token])))
    return Prepared(
        raw=raw,
        text=text,
        keyboard_fixed=changed,
        language=language_of(text),
        tokens=tokens,
        concepts=concepts,
        expansions=expand(text, tokens, kn.groups),
        sound=sound_key(unknown) if unknown and not has_thai(text) else "",
    )


def like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def credit(concept: Concept):
    """SQL: how well one chunk covers this concept, 0 to 1."""
    options = []
    for term in concept.terms:
        options.append(case((RagChunk.search_text.ilike(like(term), escape="\\"), 1.0), else_=0.0))
        if len(term) >= FUZZY_MIN_LETTERS:
            options.append(
                case((func.word_similarity(term, RagChunk.search_text) >= FUZZY_SIMILARITY, FUZZY_CREDIT), else_=0.0)
            )
    for key in concept.sounds:
        options.append(case((RagChunk.sound.ilike(like(key), escape="\\"), SOUND_CREDIT), else_=0.0))
    return func.greatest(*options) if len(options) > 1 else options[0]


async def retrieve(db: AsyncSession, raw: str) -> Retrieval:
    kn = await knowledge(db)
    prepared = prepare(raw, kn)
    if not prepared.concepts and not prepared.sound:
        return Retrieval(prepared)

    query_text = " ".join([prepared.text, *prepared.expansions])
    vector = embed(query_text, tokenize(query_text))
    total_weight = max(sum(c.weight for c in prepared.concepts), 1)

    weighted = [credit(c) * c.weight for c in prepared.concepts]
    keyword_sum = sum(weighted[1:], weighted[0]) if weighted else literal(0.0)
    trigram = func.word_similarity(query_text, RagChunk.search_text)
    distance = RagChunk.embedding.cosine_distance(vector)
    sound = func.word_similarity(prepared.sound, RagChunk.sound) if prepared.sound else literal(0.0)

    rough = (
        W_KEYWORD * cast(keyword_sum, Float) / total_weight
        + W_VECTOR * (1 - distance)
        + W_TRIGRAM * trigram
        + W_SOUND * sound
    )
    rows = (
        await db.execute(
            select(RagChunk, keyword_sum, trigram, distance, sound).order_by(rough.desc()).limit(CANDIDATES)
        )
    ).all()

    title_terms = [t for concept in prepared.concepts for t in concept.terms]
    scored: list[Hit] = []
    for chunk, covered, tri, dist, snd in rows:
        keyword = clamp(float(covered) / total_weight)
        vec = clamp((1 - float(dist) - VECTOR_FLOOR) / VECTOR_SPAN)
        tri, snd = float(tri), float(snd)
        score = W_KEYWORD * keyword + W_VECTOR * vec + W_TRIGRAM * tri + W_SOUND * snd
        title = normalize(f"{chunk.title_th} {chunk.title_en}", limit=None)
        if keyword > 0 and any(t in title for t in title_terms):
            score += TITLE_BOOST
        if keyword > 0 and len(prepared.text) >= 3 and prepared.text in chunk.search_text:
            score += PHRASE_BOOST
        scored.append(Hit(chunk, clamp(score), keyword, vec, tri, snd))
    scored.sort(key=lambda h: h.score, reverse=True)

    hits: list[Hit] = []
    per_source: dict[tuple[str, int], int] = {}
    for hit in scored:
        key = (hit.chunk.source_type, hit.chunk.source_id)
        if hit.score < MIN_HIT or per_source.get(key, 0) >= MAX_PER_SOURCE:
            continue
        per_source[key] = per_source.get(key, 0) + 1
        hits.append(hit)
        if len(hits) == MAX_HITS:
            break
    return Retrieval(prepared, hits, band_of(hits))


def band_of(hits: list[Hit]) -> str:
    """High needs a real word match, not just a similar-looking vector."""
    if not hits:
        return "low"
    top = hits[0]
    if top.score >= HIGH and top.keyword >= 0.5:
        return "high"
    return "medium" if top.score >= MEDIUM and top.keyword > 0 else "low"
