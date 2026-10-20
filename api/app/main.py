from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import RedirectResponse

from .deps import LoginRequired, current_session
from .routers import auth, categories, kinds, projects, public, tags

app = FastAPI(title="Portfolio API", docs_url="/api/docs", openapi_url="/api/openapi.json")

# Caddy sends only /api/* from the main domain and strips nothing; the admin
# host is rewritten to /admin/*. So /admin is unreachable from the public domain.
app.include_router(public.router, prefix="/api")

admin = APIRouter(prefix="/admin")
admin.include_router(auth.router)
admin.include_router(categories.router, dependencies=[Depends(current_session)])
admin.include_router(kinds.router, dependencies=[Depends(current_session)])
admin.include_router(projects.router, dependencies=[Depends(current_session)])
admin.include_router(tags.router, dependencies=[Depends(current_session)])


@admin.get("/")
async def home(_=Depends(current_session)):
    return RedirectResponse("/projects", status_code=303)


app.include_router(admin)


@app.exception_handler(LoginRequired)
async def login_required(request: Request, exc: LoginRequired):
    return RedirectResponse("/login", status_code=303)
