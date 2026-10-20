from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    # GitHub OAuth is allowlisted by this ID and attaches to this same row.
    github_user_id: Mapped[int | None] = mapped_column(Integer, unique=True)


class AuthSession(Base):
    __tablename__ = "auth_session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_th: Mapped[str] = mapped_column(String(120), default="")
    name_en: Mapped[str] = mapped_column(String(120), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    # Set when moved to the trash; cleared on restore.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Tag(Base):
    """A technology. Shared by projects now, and by work history and certificates later."""

    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    # Other names for the same thing (pg, postgres). The RAG glossary reads these.
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


project_category = Table(
    "project_category",
    Base.metadata,
    Column("project_id", ForeignKey("project.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("category.id", ondelete="CASCADE"), primary_key=True),
)

project_tag = Table(
    "project_tag",
    Base.metadata,
    Column("project_id", ForeignKey("project.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)

STATUSES = ("draft", "published", "hidden")
MAX_CATEGORIES = 3
# Text fields written in both languages: <name>_th and <name>_en on Project.
PROJECT_TEXT_FIELDS = ("title", "problem", "work", "role", "result", "learned", "next_steps")


class Kind(Base):
    """What sort of entry this is: project, certificate, award, course, activity, ..."""

    __tablename__ = "kind"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_th: Mapped[str] = mapped_column(String(120), default="")
    name_en: Mapped[str] = mapped_column(String(120), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Project(Base):
    """One entry on the site. Kind says what it is; the same fields serve every kind."""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind_id: Mapped[int | None] = mapped_column(ForeignKey("kind.id", ondelete="RESTRICT"))
    title_th: Mapped[str] = mapped_column(String(200), default="")
    title_en: Mapped[str] = mapped_column(String(200), default="")
    problem_th: Mapped[str] = mapped_column(Text, default="")
    problem_en: Mapped[str] = mapped_column(Text, default="")
    work_th: Mapped[str] = mapped_column(Text, default="")
    work_en: Mapped[str] = mapped_column(Text, default="")
    role_th: Mapped[str] = mapped_column(Text, default="")
    role_en: Mapped[str] = mapped_column(Text, default="")
    result_th: Mapped[str] = mapped_column(Text, default="")
    result_en: Mapped[str] = mapped_column(Text, default="")
    learned_th: Mapped[str] = mapped_column(Text, default="")
    learned_en: Mapped[str] = mapped_column(Text, default="")
    next_steps_th: Mapped[str] = mapped_column(Text, default="")
    next_steps_en: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer)
    # Generic fields a certificate, award or course fills in; other kinds leave them empty.
    issuer: Mapped[str] = mapped_column(String(200), default="")
    issued_on: Mapped[date | None] = mapped_column(Date)
    verify_url: Mapped[str] = mapped_column(String(500), default="")
    repo_url: Mapped[str] = mapped_column(String(500), default="")
    demo_url: Mapped[str] = mapped_column(String(500), default="")
    # Other names people may use for this project. The RAG glossary reads these.
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    kind: Mapped[Kind | None] = relationship(lazy="selectin")
    categories: Mapped[list[Category]] = relationship(
        secondary=project_category, lazy="selectin", order_by="(Category.sort_order, Category.id)"
    )
    tags: Mapped[list[Tag]] = relationship(secondary=project_tag, lazy="selectin", order_by="Tag.name")
    # Live images only, cover first by sort order. Trashed ones are queried directly in the admin.
    images: Mapped[list["ProjectImage"]] = relationship(
        lazy="selectin",
        order_by="(ProjectImage.sort_order, ProjectImage.id)",
        primaryjoin="and_(Project.id == ProjectImage.project_id, ProjectImage.deleted_at.is_(None))",
        viewonly=True,
    )


work_tag = Table(
    "work_tag",
    Base.metadata,
    Column("work_entry_id", ForeignKey("work_entry.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)

# key -> (Thai label, English label). "event" is a short activity placed on the timeline.
EMPLOYMENT_TYPES = {
    "full_time": ("งานประจำ", "Full-time"),
    "part_time": ("พาร์ทไทม์", "Part-time"),
    "contract": ("สัญญาจ้าง", "Contract"),
    "freelance": ("ฟรีแลนซ์", "Freelance"),
    "internship": ("ฝึกงาน", "Internship"),
    "event": ("กิจกรรม / งานสั้น", "Event / short gig"),
    "other": ("อื่น ๆ", "Other"),
}
# How an entry spans time. Derived from the dates, never stored.
SPANS = ("range", "ongoing", "moment")


class WorkEntry(Base):
    """One item on the timeline. A long job, a job still running, or a single day.
    Role, place and dates only; no confidential company detail."""

    __tablename__ = "work_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    position_th: Mapped[str] = mapped_column(String(200), default="")
    position_en: Mapped[str] = mapped_column(String(200), default="")
    # Employer, or the organizer for an event. May be empty for an event.
    employer: Mapped[str] = mapped_column(String(200), default="")
    employment_type: Mapped[str] = mapped_column(String(20), default="full_time")
    started_on: Mapped[date] = mapped_column(Date)
    # Set: a range, or a single day when equal to started_on. Empty and ongoing: still running.
    ended_on: Mapped[date | None] = mapped_column(Date)
    ongoing: Mapped[bool] = mapped_column(Boolean, default=False)
    # One bullet per line.
    bullets_th: Mapped[str] = mapped_column(Text, default="")
    bullets_en: Mapped[str] = mapped_column(Text, default="")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tags: Mapped[list[Tag]] = relationship(secondary=work_tag, lazy="selectin", order_by="Tag.name")

    @property
    def span(self) -> str:
        if self.ongoing:
            return "ongoing"
        return "moment" if self.ended_on is None or self.ended_on == self.started_on else "range"


# key -> (Thai label, English label)
EDUCATION_LEVELS = {
    "high_school": ("มัธยมศึกษา", "High school"),
    "vocational": ("อาชีวศึกษา (ปวช. / ปวส.)", "Vocational"),
    "bachelor": ("ปริญญาตรี", "Bachelor's degree"),
    "master": ("ปริญญาโท", "Master's degree"),
    "doctorate": ("ปริญญาเอก", "Doctorate"),
    "certificate": ("ประกาศนียบัตร / หลักสูตรระยะสั้น", "Certificate / short program"),
    "other": ("อื่น ๆ", "Other"),
}


class EducationEntry(Base):
    """One school, degree or formal program. Month precision; an unfinished one is marked ongoing."""

    __tablename__ = "education_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_th: Mapped[str] = mapped_column(String(200), default="")
    institution_en: Mapped[str] = mapped_column(String(200), default="")
    level: Mapped[str] = mapped_column(String(20), default="bachelor")
    degree_th: Mapped[str] = mapped_column(String(200), default="")  # e.g. วิทยาศาสตรบัณฑิต
    degree_en: Mapped[str] = mapped_column(String(200), default="")  # e.g. B.Sc.
    field_th: Mapped[str] = mapped_column(String(200), default="")  # major
    field_en: Mapped[str] = mapped_column(String(200), default="")
    grade: Mapped[str] = mapped_column(String(60), default="")  # "GPA 3.45", "เกียรตินิยมอันดับหนึ่ง"; only what a transcript shows
    started_on: Mapped[date] = mapped_column(Date)  # always the first day of the month
    ended_on: Mapped[date | None] = mapped_column(Date)
    ongoing: Mapped[bool] = mapped_column(Boolean, default=False)
    # One item per line: thesis, honors, activities.
    details_th: Mapped[str] = mapped_column(Text, default="")
    details_en: Mapped[str] = mapped_column(Text, default="")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def span(self) -> str:
        return "ongoing" if self.ongoing else "range"


article_tag = Table(
    "article_tag",
    Base.metadata,
    Column("article_id", ForeignKey("article.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)

ARTICLE_SOURCES = ("internal", "external")


class Article(Base):
    """Written on this site (source=internal) or a link to another platform (source=external)."""

    __tablename__ = "article"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_th: Mapped[str] = mapped_column(String(200), default="")
    title_en: Mapped[str] = mapped_column(String(200), default="")
    summary_th: Mapped[str] = mapped_column(Text, default="")
    summary_en: Mapped[str] = mapped_column(Text, default="")
    # Markdown text, served as-is; the front end renders it. Empty for external articles.
    body_th: Mapped[str] = mapped_column(Text, default="")
    body_en: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default="internal")
    external_url: Mapped[str] = mapped_column(String(500), default="")
    platform: Mapped[str] = mapped_column(String(80), default="")  # Medium, dev.to, ...
    published_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tags: Mapped[list[Tag]] = relationship(secondary=article_tag, lazy="selectin", order_by="Tag.name")


class Profile(Base):
    """The owner's details for the home page. One row, id 1."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_th: Mapped[str] = mapped_column(String(120), default="")
    name_en: Mapped[str] = mapped_column(String(120), default="")
    intro_th: Mapped[str] = mapped_column(Text, default="")
    intro_en: Mapped[str] = mapped_column(Text, default="")
    location_th: Mapped[str] = mapped_column(String(200), default="")
    location_en: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    # Files live in object storage; an empty key means nothing uploaded.
    photo_key: Mapped[str] = mapped_column(String(200), default="")
    photo_content_type: Mapped[str] = mapped_column(String(50), default="")
    cv_th_key: Mapped[str] = mapped_column(String(200), default="")
    cv_th_name: Mapped[str] = mapped_column(String(200), default="")
    cv_en_key: Mapped[str] = mapped_column(String(200), default="")
    cv_en_name: Mapped[str] = mapped_column(String(200), default="")


class ContactLink(Base):
    """GitHub, LinkedIn, Medium, ... shown next to the email."""

    __tablename__ = "contact_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    url: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SiteSettings(Base):
    """How many items each public section shows. One row, id 1."""

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    featured_limit: Mapped[int] = mapped_column(Integer, default=6)
    projects_page_size: Mapped[int] = mapped_column(Integer, default=12)
    articles_page_size: Mapped[int] = mapped_column(Integer, default=12)
    # The one project the "how I work" section tells the story through. Empty: the section is hidden.
    how_i_work_project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="SET NULL"))


class GlossaryEntry(Base):
    """Words that mean the same thing (สต็อก, stock, inventory). A question using one finds text using another."""

    __tablename__ = "glossary_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    terms: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    note: Mapped[str] = mapped_column(String(200), default="")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


EMBED_DIM = 384


class RagChunk(Base):
    """One searchable piece of the site: a project, or one section of it, a job, an article part, the profile.
    Rebuilt from the content whenever the owner presses "rebuild"; nothing here is edited by hand."""

    __tablename__ = "rag_chunk"
    __table_args__ = (
        Index("ix_rag_chunk_search_trgm", "search_text", postgresql_using="gin", postgresql_ops={"search_text": "gin_trgm_ops"}),
        Index("ix_rag_chunk_sound_trgm", "sound", postgresql_using="gin", postgresql_ops={"sound": "gin_trgm_ops"}),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(16))  # project | work | article | profile
    source_id: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(24), default="")
    title_th: Mapped[str] = mapped_column(String(300), default="")
    title_en: Mapped[str] = mapped_column(String(300), default="")
    # What the model is shown when it answers.
    body_th: Mapped[str] = mapped_column(Text, default="")
    body_en: Mapped[str] = mapped_column(Text, default="")
    # What is searched: both languages, tags, aliases and glossary names, normalized.
    search_text: Mapped[str] = mapped_column(Text, default="")
    sound: Mapped[str] = mapped_column(Text, default="")  # phonetic key for Thai typed in Latin letters
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RagQuery(Base):
    """Every question asked in the question box, and what became of it. Read by the owner to find
    what visitors want that the site does not answer yet, and reused as the answer cache."""

    __tablename__ = "rag_query"
    __table_args__ = (
        Index("ix_rag_query_ip_created", "ip_hash", "created_at"),
        Index("ix_rag_query_cache", "cache_key", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_hash: Mapped[str] = mapped_column(String(16), default="")
    question: Mapped[str] = mapped_column(String(300), default="")
    normalized: Mapped[str] = mapped_column(String(300), default="")
    language: Mapped[str] = mapped_column(String(8), default="")
    band: Mapped[str] = mapped_column(String(8), default="")  # high | medium | low
    top_score: Mapped[float] = mapped_column(Float, default=0.0)
    # answer | uncertain | no_answer | fallback | redirect | greeting | blocked
    mode: Mapped[str] = mapped_column(String(16), default="")
    tier: Mapped[str] = mapped_column(String(8), default="")  # which model was asked: cheap | smart | ""
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    cache_key: Mapped[str] = mapped_column(String(32), default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    sources: Mapped[list] = mapped_column(JSON, default=list)


class ProjectImage(Base):
    """A picture or screenshot of one entry. The file lives in object storage under `key`."""

    __tablename__ = "project_image"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(200), unique=True)
    content_type: Mapped[str] = mapped_column(String(50))
    size: Mapped[int] = mapped_column(Integer)
    caption_th: Mapped[str] = mapped_column(String(300), default="")
    caption_en: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)
    # Set when moved to the trash; the file stays in storage.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
