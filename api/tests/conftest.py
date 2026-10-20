import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_test"
)

import pyotp
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.main import app
from app.models import Base, User
from app.ratelimit import login_limiter
from app.security import hash_password
from app.storage import get_storage

EMAIL = "arm@example.com"
PASSWORD = "correct horse battery"
TOTP_SECRET = pyotp.random_base32()


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    login_limiter.reset()
    async with SessionLocal() as db:
        db.add(User(email=EMAIL, password_hash=hash_password(PASSWORD), totp_secret=TOTP_SECRET))
        await db.commit()


class MemoryStorage:
    """Stands in for S3 so tests need no storage container."""

    def __init__(self):
        self.files: dict[str, tuple[bytes, str]] = {}

    async def put(self, key, data, content_type):
        self.files[key] = (data, content_type)

    async def get(self, key):
        return self.files[key][0] if key in self.files else None

    async def delete(self, key):
        self.files.pop(key, None)


@pytest.fixture(autouse=True)
def storage():
    fake = MemoryStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_storage, None)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://admin.test") as c:
        yield c


async def csrf_from_login_page(client) -> str:
    page = await client.get("/admin/login")
    assert page.status_code == 200
    return client.cookies["login_csrf"]


async def login(client, password=PASSWORD, code=None, email=EMAIL):
    token = await csrf_from_login_page(client)
    return await client.post(
        "/admin/login",
        data={
            "email": email,
            "password": password,
            "code": code if code is not None else pyotp.TOTP(TOTP_SECRET).now(),
            "csrf_token": token,
        },
    )


@pytest_asyncio.fixture
async def authed(client):
    resp = await login(client)
    assert resp.status_code == 303
    async with SessionLocal() as db:
        row = (await db.execute(text("select csrf_token from auth_session"))).one()
    client.csrf = row[0]
    return client
