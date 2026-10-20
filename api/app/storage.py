"""Object storage behind one small interface. Endpoint and keys come from the environment,
so moving from the local container to a real S3 service changes no code."""
from functools import lru_cache
from typing import Protocol

import boto3
from anyio import to_thread
from botocore.client import Config
from botocore.exceptions import ClientError

from .config import get_settings


class Storage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes | None: ...
    async def delete(self, key: str) -> None: ...


class S3Storage:
    def __init__(self) -> None:
        s = get_settings()
        self.bucket = s.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint,
            aws_access_key_id=s.s3_access_key,
            aws_secret_access_key=s.s3_secret_key,
            region_name="us-east-1",
            config=Config(s3={"addressing_style": "path"}),
        )
        self.ready = False

    def _ensure_bucket(self) -> None:
        if self.ready:
            return
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)
        self.ready = True

    def _put(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def _get(self, key: str) -> bytes | None:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await to_thread.run_sync(self._put, key, data, content_type)

    async def get(self, key: str) -> bytes | None:
        return await to_thread.run_sync(self._get, key)

    async def delete(self, key: str) -> None:
        await to_thread.run_sync(lambda: self.client.delete_object(Bucket=self.bucket, Key=key))


@lru_cache
def get_storage() -> Storage:
    return S3Storage()
