import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base

target_metadata = Base.metadata


def run_sync(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run() -> None:
    url = os.environ.get("ALEMBIC_DATABASE_URL") or get_settings().database_url
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        await connection.run_sync(run_sync)
    await engine.dispose()


asyncio.run(run())
