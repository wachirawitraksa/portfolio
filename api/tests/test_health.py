import asyncio
import logging
import time

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.db import get_db
from app.main import app
from app.storage import S3Storage, get_storage


class BrokenStorage:
    def __init__(self, error: Exception | None = None, delay: float = 0.0):
        self.error, self.delay = error, delay

    async def ping(self):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error


class BrokenSession:
    async def execute(self, *args, **kwargs):
        raise ConnectionRefusedError("password=hunter2 host=db")


@pytest.fixture
def override():
    def apply(storage=None, db=None):
        if storage is not None:
            app.dependency_overrides[get_storage] = lambda: storage
        if db is not None:

            async def session():
                yield db

            app.dependency_overrides[get_db] = session

    yield apply
    app.dependency_overrides.pop(get_db, None)  # get_storage is reset by the autouse fixture in conftest


async def test_everything_up_is_200_and_not_cached(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200 and resp.json() == {"status": "ok", "database": "ok", "storage": "ok"}
    assert resp.headers["cache-control"] == "no-store"


async def test_live_only_says_the_process_answers(client):
    resp = await client.get("/api/health/live")
    assert resp.status_code == 200 and resp.json() == {"status": "ok"} and resp.headers["cache-control"] == "no-store"


async def test_a_dead_storage_is_503_and_names_only_the_part_that_failed(client, override, caplog):
    override(storage=BrokenStorage(EndpointConnectionError(endpoint_url="http://secret-host:9000")))
    with caplog.at_level(logging.WARNING, logger="portfolio.health"):
        resp = await client.get("/api/health")
    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "database": "ok", "storage": "fail"}
    assert "secret-host" not in resp.text  # the reason is for the log only
    assert "storage check failed" in caplog.text and "secret-host" in caplog.text


async def test_a_dead_database_is_503(client, override):
    override(db=BrokenSession())
    resp = await client.get("/api/health")
    assert resp.status_code == 503 and resp.json() == {"status": "degraded", "database": "fail", "storage": "ok"}
    assert "hunter2" not in resp.text


async def test_both_down_is_503_but_live_still_answers(client, override):
    override(storage=BrokenStorage(RuntimeError("no")), db=BrokenSession())
    assert (await client.get("/api/health")).json() == {"status": "degraded", "database": "fail", "storage": "fail"}
    assert (await client.get("/api/health/live")).status_code == 200  # the process itself is fine


async def test_a_slow_storage_counts_as_down_instead_of_hanging(client, override, monkeypatch):
    monkeypatch.setattr("app.routers.health.STORAGE_TIMEOUT", 0.05)
    override(storage=BrokenStorage(delay=5))
    started = time.monotonic()
    resp = await client.get("/api/health")
    assert resp.status_code == 503 and resp.json()["storage"] == "fail"
    assert time.monotonic() - started < 2


async def test_health_needs_no_login(client):
    assert not client.cookies  # a visitor with no session
    assert (await client.get("/api/health")).status_code == 200


# --- the real storage adapter's ping -----------------------------------------------------------


class FakeS3:
    def __init__(self, outcome):
        self.outcome = outcome

    def head_bucket(self, Bucket):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return {}


def s3_with(outcome) -> S3Storage:
    storage = S3Storage()
    storage.client = FakeS3(outcome)
    return storage


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": "x"}}, "HeadBucket")


async def test_s3_ping_is_ok_when_the_bucket_answers():
    await s3_with(None).ping()


@pytest.mark.parametrize("code", ["404", "NoSuchBucket", "NotFound"])
async def test_s3_ping_treats_a_missing_bucket_as_reachable(code):
    await s3_with(client_error(code)).ping()  # the first upload creates the bucket


@pytest.mark.parametrize(
    "error",
    [client_error("403"), client_error("500"), EndpointConnectionError(endpoint_url="http://x:9000"), TimeoutError("slow")],
)
async def test_s3_ping_fails_on_real_problems(error):
    with pytest.raises(Exception):
        await s3_with(error).ping()
