from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuthSession


async def revoke_all_sessions(db: AsyncSession, user_id: int) -> None:
    """End every login of this user. Used whenever the password or TOTP secret changes."""
    await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
