"""Shapes of the public API (/api/*). They exist so the OpenAPI document, and the TypeScript types the
website is generated from it, describe real fields instead of `any`. The routes return plain dicts;
FastAPI checks them against these models on the way out, so a mismatch fails in the tests, not in a browser.

Dates are ISO strings ("2025-06-30"). A missing optional value is null."""
from typing import Literal

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: int
    name_th: str
    name_en: str


class KindOut(BaseModel):
    id: int
    name_th: str
    name_en: str


class TagRef(BaseModel):
    id: int
    name: str


class TagCount(TagRef):
    count: int  # public projects that use the tag


class ImageOut(BaseModel):
    id: int
    url: str  # e.g. /api/media/12, same host as the API
    caption_th: str
    caption_en: str
    is_cover: bool


class ProjectCard(BaseModel):
    """What a card in a list needs."""

    id: int
    title_th: str
    title_en: str
    problem_th: str
    problem_en: str
    year: int | None
    cover_url: str | None
    repo_url: str
    demo_url: str
    verify_url: str
    issuer: str
    issued_on: str | None
    featured: bool
    kind: KindOut | None
    categories: list[CategoryOut]
    tags: list[TagRef]


class ProjectDetail(ProjectCard):
    work_th: str
    work_en: str
    role_th: str
    role_en: str
    result_th: str
    result_en: str
    learned_th: str
    learned_en: str
    next_steps_th: str
    next_steps_en: str
    images: list[ImageOut]


class ProjectList(BaseModel):
    total: int  # all matches, not only this page
    items: list[ProjectCard]


class WorkItem(BaseModel):
    """One item on the timeline: a long range, ongoing work, or a single day."""

    id: int
    position_th: str
    position_en: str
    employer: str
    employment_type: str
    employment_type_th: str
    employment_type_en: str
    span: Literal["range", "ongoing", "moment"]
    started_on: str
    ended_on: str | None  # null while ongoing; a single day repeats started_on
    bullets_th: list[str]
    bullets_en: list[str]
    tags: list[TagRef]


class ArticleCard(BaseModel):
    id: int
    title_th: str
    title_en: str
    summary_th: str
    summary_en: str
    source: Literal["internal", "external"]
    platform: str
    external_url: str
    published_on: str | None
    tags: list[TagRef]


class ArticleDetail(ArticleCard):
    body_th: str  # Markdown; empty for an article that lives on another platform
    body_en: str


class ArticleList(BaseModel):
    total: int
    items: list[ArticleCard]


class ContactLinkOut(BaseModel):
    id: int
    label: str
    url: str


class ProfileOut(BaseModel):
    name_th: str
    name_en: str
    intro_th: str
    intro_en: str
    location_th: str
    location_en: str
    email: str
    photo_url: str | None
    cv_th_url: str | None
    cv_en_url: str | None
    links: list[ContactLinkOut]


class SettingsOut(BaseModel):
    featured_limit: int
    projects_page_size: int
    articles_page_size: int
    how_i_work_project_id: int | None


class AskIn(BaseModel):
    question: str = Field(max_length=1000)


class AskSource(BaseModel):
    type: Literal["project", "work", "article", "profile"]
    id: int
    section: str
    title_th: str
    title_en: str


class AskOut(BaseModel):
    answer: str
    mode: Literal["answer", "uncertain", "no_answer", "fallback", "redirect", "greeting", "blocked", "rate_limited"]
    confidence: Literal["high", "medium", "low"]
    sources: list[AskSource]
    cached: bool
    contact_email: str
