from __future__ import annotations

import logging

import aioboto3
from botocore.exceptions import ClientError

from app.application.storage.ports import StorageGateway, UploadedFile
from app.core.config import settings

logger = logging.getLogger(__name__)


class S3StorageGateway(StorageGateway):
    def __init__(self) -> None:
        self._session = aioboto3.Session()

    def _client(self):
        return self._session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )

    async def _ensure_bucket(self, client, bucket: str) -> None:
        try:
            await client.head_bucket(Bucket=bucket)
        except ClientError:
            await client.create_bucket(Bucket=bucket)
            logger.info("S3StorageGateway: created bucket %s", bucket)

    async def upload(self, *, bucket: str, key: str, data: bytes, content_type: str) -> UploadedFile:
        async with self._client() as client:
            await self._ensure_bucket(client, bucket)
            await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        url = f"{settings.S3_PUBLIC_BASE_URL}/{bucket}/{key}"
        logger.info("S3StorageGateway: uploaded key=%s size=%d", key, len(data))
        return UploadedFile(key=key, url=url, size=len(data), content_type=content_type)

    async def delete(self, *, bucket: str, key: str) -> None:
        async with self._client() as client:
            await client.delete_object(Bucket=bucket, Key=key)
        logger.info("S3StorageGateway: deleted key=%s from bucket=%s", key, bucket)
