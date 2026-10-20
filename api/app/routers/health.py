import asyncio
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..schemas import HealthOut, LiveOut
from ..storage import Storage, get_storage

router = APIRouter()
log = logging.getLogger("portfolio.health")

DATABASE_TIMEOUT = 2.0  # seconds a check may take before it counts as failed
STORAGE_TIMEOUT = 4.0
NO_CACHE = {"Cache-Control": "no-store"}


async def check(name: str, probe, timeout: float) -> str:
    try:
        await asyncio.wait_for(probe(), timeout)
        return "ok"
    except Exception as error:  # the reason goes to the log, never to the caller
        log.warning("health: %s check failed: %s: %s", name, type(error).__name__, error)
        return "fail"


@router.get("/health/live", response_model=LiveOut)
async def live():
    """The process is up and answering. Touches nothing else."""
    return JSONResponse({"status": "ok"}, headers=NO_CACHE)


@router.get(
    "/health",
    response_model=HealthOut,
    responses={503: {"model": HealthOut, "description": "The database or the file storage is not answering"}},
)
async def health(db: AsyncSession = Depends(get_db), storage: Storage = Depends(get_storage)):
    """200 when the database and the file storage both answer, 503 when either does not. For monitoring
    and for the container health check."""
    database = await check("database", lambda: db.execute(text("select 1")), DATABASE_TIMEOUT)
    stored = await check("storage", storage.ping, STORAGE_TIMEOUT)
    ok = database == "ok" and stored == "ok"
    return JSONResponse(
        {"status": "ok" if ok else "degraded", "database": database, "storage": stored},
        status_code=200 if ok else 503,
        headers=NO_CACHE,
    )
