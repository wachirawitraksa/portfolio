from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Table, Text, func
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
