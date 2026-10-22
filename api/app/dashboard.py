"""The numbers and the to-do list behind the admin home page."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .forms import untranslated as project_gaps
from .github import enabled as github_enabled
from .models import (
    Article,
    Category,
    ContactLink,
    EducationEntry,
    GlossaryEntry,
    Kind,
    Project,
    ProjectImage,
    RagQuery,
    Tag,
    WorkEntry,
)
from .rag.index import index_status
from .routers.articles import untranslated as article_gaps
from .routers.education import untranslated as education_gaps
from .routers.health import DATABASE_TIMEOUT, STORAGE_TIMEOUT, check
from .routers.profile import untranslated as profile_gaps
from .routers.work import untranslated as work_gaps
from .site import get_profile
from .storage import Storage
from .trash import ENTRIES

UNANSWERED = ("no_answer", "fallback")


async def scalar(db: AsyncSession, query) -> int:
    return (await db.execute(query)).scalar_one()


async def by_status(db: AsyncSession, model) -> dict[str, int]:
    rows = (
        await db.execute(select(model.status, func.count()).where(model.deleted_at.is_(None)).group_by(model.status))
    ).all()
    return {status: n for status, n in rows}


async def trash_total(db: AsyncSession) -> int:
    return sum([await scalar(db, select(func.count()).select_from(e.model).where(e.model.deleted_at.is_not(None))) for e in ENTRIES.values()])


async def health(db: AsyncSession, storage: Storage) -> dict[str, str]:
    from sqlalchemy import text

    return {
        "database": await check("database", lambda: db.execute(text("select 1")), DATABASE_TIMEOUT),
        "storage": await check("storage", storage.ping, STORAGE_TIMEOUT),
    }


async def overview(db: AsyncSession, storage: Storage) -> dict:
    settings = get_settings()
    now = datetime.now(timezone.utc)

    projects = await by_status(db, Project)
    articles = await by_status(db, Article)
    work_live = await scalar(db, select(func.count()).select_from(WorkEntry).where(WorkEntry.deleted_at.is_(None)))
    work_hidden = await scalar(
        db, select(func.count()).select_from(WorkEntry).where(WorkEntry.deleted_at.is_(None), WorkEntry.hidden.is_(True))
    )
    education_live = await scalar(db, select(func.count()).select_from(EducationEntry).where(EducationEntry.deleted_at.is_(None)))
    education_hidden = await scalar(
        db, select(func.count()).select_from(EducationEntry).where(EducationEntry.deleted_at.is_(None), EducationEntry.hidden.is_(True))
    )
    images = await scalar(db, select(func.count()).select_from(ProjectImage).where(ProjectImage.deleted_at.is_(None)))
    has_image = select(ProjectImage.project_id).where(ProjectImage.deleted_at.is_(None))
    published_without_image = await scalar(
        db,
        select(func.count()).select_from(Project).where(
            Project.status == "published", Project.deleted_at.is_(None), Project.id.not_in(has_image)
        ),
    )
    counts = {
        "tags": await scalar(db, select(func.count()).select_from(Tag).where(Tag.deleted_at.is_(None))),
        "categories": await scalar(db, select(func.count()).select_from(Category).where(Category.deleted_at.is_(None))),
        "kinds": await scalar(db, select(func.count()).select_from(Kind).where(Kind.deleted_at.is_(None))),
        "glossary": await scalar(db, select(func.count()).select_from(GlossaryEntry).where(GlossaryEntry.deleted_at.is_(None))),
    }

    # Questions: the last day for the cost picture, the last week for what is still unanswered.
    day_ago, week_ago = now - timedelta(days=1), now - timedelta(days=7)
    asked_today = await scalar(db, select(func.count()).select_from(RagQuery).where(RagQuery.created_at > day_ago))
    model_calls = await scalar(
        db, select(func.count()).select_from(RagQuery).where(RagQuery.created_at > day_ago, RagQuery.tier != "", RagQuery.cached.is_(False))
    )
    unanswered = await scalar(
        db, select(func.count()).select_from(RagQuery).where(RagQuery.created_at > week_ago, RagQuery.mode.in_(UNANSWERED))
    )
    # A good match answered with "go and read it yourself" means the model could not be reached (retired model,
    # quota, bad key, outage). Only counted when a key is set: without one the fallback is the intended behaviour.
    llm_failures = 0
    if settings.gemini_api_key:
        llm_failures = await scalar(
            db,
            select(func.count()).select_from(RagQuery).where(
                RagQuery.created_at > day_ago, RagQuery.mode == "fallback", RagQuery.band != "low", RagQuery.cached.is_(False)
            ),
        )

    # Translation gaps: text filled in one language and empty in the other.
    live_projects = (await db.execute(select(Project).where(Project.deleted_at.is_(None)))).scalars().all()
    live_work = (await db.execute(select(WorkEntry).where(WorkEntry.deleted_at.is_(None)))).scalars().all()
    live_articles = (await db.execute(select(Article).where(Article.deleted_at.is_(None)))).scalars().all()
    live_education = (await db.execute(select(EducationEntry).where(EducationEntry.deleted_at.is_(None)))).scalars().all()
    profile = await get_profile(db)
    gaps = {
        "ผลงาน": sum(1 for p in live_projects if project_gaps(p)),
        "ประวัติการทำงาน": sum(1 for w in live_work if work_gaps(w)),
        "ประวัติการศึกษา": sum(1 for e in live_education if education_gaps(e)),
        "บทความ": sum(1 for a in live_articles if article_gaps(a)),
        "ข้อมูลส่วนตัว": 1 if profile_gaps(profile) else 0,
    }

    missing_profile = [
        label
        for label, ok in (
            ("ชื่อ", profile.name_th or profile.name_en),
            ("แนะนำตัว", profile.intro_th or profile.intro_en),
            ("รูป", profile.photo_key),
            ("อีเมล", profile.email),
            ("CV", profile.cv_th_key or profile.cv_en_key),
            ("ช่องทางติดต่อ", await scalar(db, select(func.count()).select_from(ContactLink).where(ContactLink.deleted_at.is_(None)))),
        )
        if not ok
    ]

    index = await index_status(db)
    trashed = await trash_total(db)
    status = await health(db, storage)

    # What needs the owner's attention, most important first. level: warn | info
    todo: list[dict] = []
    if any(v == "fail" for v in status.values()):
        failed = " และ ".join({"database": "ฐานข้อมูล", "storage": "ที่เก็บไฟล์"}[k] for k, v in status.items() if v == "fail")
        todo.append({"level": "warn", "text": f"{failed}ไม่ตอบสนอง", "href": "/", "cta": "ดูสถานะ"})
    if llm_failures:
        todo.append({"level": "warn", "text": f"โมเดลตอบคำถามล้มเหลว {llm_failures} ครั้งใน 24 ชั่วโมงที่ผ่านมา ผู้เข้าชมได้คำตอบแบบพาไปอ่านเองแทน (ดูสาเหตุ: docker logs portfolio-api)", "href": "/rag/questions", "cta": "ดูคำถาม"})
    if index["stale"]:
        parts = [f"{label} {index[key]}" for label, key in (("เพิ่มใหม่", "added"), ("ถูกแก้", "changed"), ("ถูกลบ", "removed")) if index[key]]
        todo.append({"level": "warn", "text": f"ข้อมูลช่องถามตอบล้าสมัย ({' · '.join(parts)} ชิ้น)", "href": "/rag", "cta": "สร้างข้อมูลใหม่"})
    if unanswered:
        todo.append({"level": "info", "text": f"มีคำถามที่ตอบไม่ได้ {unanswered} ข้อใน 7 วันนี้ (เอาไปเติมเนื้อหาได้)", "href": "/rag/questions", "cta": "ดูคำถาม"})
    if not projects.get("published") and not projects.get("draft") and not projects.get("hidden"):
        todo.append({"level": "info", "text": "ยังไม่มีผลงาน เริ่มเพิ่มชิ้นแรกได้เลย", "href": "/projects/new", "cta": "เพิ่มผลงาน"})
    if projects.get("draft"):
        todo.append({"level": "info", "text": f"มีผลงานฉบับร่าง {projects['draft']} ชิ้นที่ยังไม่เผยแพร่", "href": "/projects", "cta": "ดูรายการ"})
    if articles.get("draft"):
        todo.append({"level": "info", "text": f"มีบทความฉบับร่าง {articles['draft']} ชิ้น", "href": "/articles", "cta": "ดูบทความ"})
    if published_without_image:
        todo.append({"level": "info", "text": f"ผลงานที่เผยแพร่แล้วแต่ยังไม่มีรูป {published_without_image} ชิ้น", "href": "/projects", "cta": "เพิ่มรูป"})
    for label, n in gaps.items():
        if n:
            href = {"ผลงาน": "/projects", "ประวัติการทำงาน": "/work", "ประวัติการศึกษา": "/education", "บทความ": "/articles", "ข้อมูลส่วนตัว": "/profile"}[label]
            todo.append({"level": "info", "text": f"{label}ที่ยังแปลไม่ครบสองภาษา {n} รายการ", "href": href, "cta": "ไปแปล"})
    if missing_profile:
        todo.append({"level": "info", "text": "ข้อมูลส่วนตัวหน้าแรกยังไม่ครบ: " + ", ".join(missing_profile), "href": "/profile", "cta": "กรอกข้อมูล"})
    if not settings.gemini_api_key:
        todo.append({"level": "info", "text": "ยังไม่ได้ตั้ง GEMINI_API_KEY ช่องถามตอบจึงตอบแบบพาไปอ่านส่วนที่เกี่ยวข้อง (ยังไม่สรุปคำตอบ)", "href": "/rag", "cta": "ดูสถานะ"})
    if trashed:
        todo.append({"level": "info", "text": f"มีของในถังขยะ {trashed} รายการ", "href": "/trash", "cta": "เปิดถังขยะ"})

    return {
        "projects": projects,
        "articles": articles,
        "work": {"live": work_live, "hidden": work_hidden},
        "education": {"live": education_live, "hidden": education_hidden},
        "images": images,
        "counts": counts,
        "questions": {"asked": asked_today, "model_calls": model_calls, "unanswered": unanswered, "llm_failures": llm_failures},
        "trashed": trashed,
        "health": status,
        "index": index,
        "gemini": bool(settings.gemini_api_key),
        "github": github_enabled(),
        "todo": todo,
    }
