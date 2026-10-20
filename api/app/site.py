"""The two single-row tables (profile, settings). Created on first use if the row is missing."""
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Profile, SiteSettings


async def get_profile(db: AsyncSession) -> Profile:
    row = await db.get(Profile, 1)
    if row is None:
        row = Profile(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def get_site_settings(db: AsyncSession) -> SiteSettings:
    row = await db.get(SiteSettings, 1)
    if row is None:
        row = SiteSettings(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row
