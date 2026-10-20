from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .deps import LoginRequired, current_session
from .routers import (
    account,
    articles,
    ask,
    auth,
    categories,
    dashboard,
    education,
    glossary,
    health,
    images,
    kinds,
    profile,
    projects,
    public,
    rag_admin,
    settings,
    tags,
    trash,
    work,
)

app = FastAPI(title="Portfolio API", docs_url="/api/docs", openapi_url="/api/openapi.json")

# The admin's stylesheet, script and htmx, served from here (on the admin host it is /static/...).
# Nothing is loaded from another site, so the login page runs no third-party code.
app.mount("/admin/static", StaticFiles(directory=Path(__file__).parent / "static"), name="admin-static")

# Caddy sends only /api/* from the main domain and strips nothing; the admin
# host is rewritten to /admin/*. So /admin is unreachable from the public domain.
app.include_router(public.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
app.include_router(health.router, prefix="/api")

admin = APIRouter(prefix="/admin")
admin.include_router(auth.router)
admin.include_router(categories.router, dependencies=[Depends(current_session)])
admin.include_router(kinds.router, dependencies=[Depends(current_session)])
admin.include_router(projects.router, dependencies=[Depends(current_session)])
admin.include_router(images.router, dependencies=[Depends(current_session)])
admin.include_router(images.preview, dependencies=[Depends(current_session)])
admin.include_router(tags.router, dependencies=[Depends(current_session)])
admin.include_router(work.router, dependencies=[Depends(current_session)])
admin.include_router(education.router, dependencies=[Depends(current_session)])
admin.include_router(articles.router, dependencies=[Depends(current_session)])
admin.include_router(profile.router, dependencies=[Depends(current_session)])
admin.include_router(settings.router, dependencies=[Depends(current_session)])
admin.include_router(account.router, dependencies=[Depends(current_session)])
admin.include_router(glossary.router, dependencies=[Depends(current_session)])
admin.include_router(rag_admin.router, dependencies=[Depends(current_session)])
admin.include_router(trash.router, dependencies=[Depends(current_session)])
admin.include_router(dashboard.router, dependencies=[Depends(current_session)])


# The admin pages are HTML for one person: keep them out of the public OpenAPI document (/api/openapi.json),
# which the website's TypeScript types are generated from.
app.include_router(admin, include_in_schema=False)


@app.exception_handler(LoginRequired)
async def login_required(request: Request, exc: LoginRequired):
    return RedirectResponse("/login", status_code=303)
