from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..dashboard import overview
from ..db import get_db
from ..deps import current_session
from ..models import AuthSession
from ..storage import Storage, get_storage
from ..templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: AuthSession = Depends(current_session),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    """The admin home: what the site contains, how the question box is doing, and what needs attention."""
    context = {**await overview(db, storage), "csrf": session.csrf_token}
    return templates.TemplateResponse(request, "dashboard.html", context)
