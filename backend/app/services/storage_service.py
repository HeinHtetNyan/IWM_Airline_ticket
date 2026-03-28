from __future__ import annotations

import asyncio
from pathlib import Path

import boto3
from fastapi import UploadFile

from backend.app.core.config import settings


class StorageService:
    async def save(self, file: UploadFile, path: str) -> str:
        raise NotImplementedError

    async def delete(self, path: str) -> None:
        raise NotImplementedError

    async def generate_presigned_url(self, path: str, expires: int = 300) -> str:
        raise NotImplementedError


class LocalStorageService(StorageService):
    async def save(self, file: UploadFile, path: str) -> str:
        destination = Path(settings.UPLOAD_DIR) / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        await file.seek(0)

        # Stream to disk in chunks so large uploads do not have to be buffered
        # fully in memory before saving.
        with destination.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                await asyncio.to_thread(buffer.write, chunk)

        await file.seek(0)

        # Only public files are exposed through the static /files mount.
        return f"{settings.BASE_URL.rstrip('/')}/files/{path}"

    async def delete(self, path: str) -> None:
        target = Path(settings.UPLOAD_DIR) / path
        if target.exists():
            await asyncio.to_thread(target.unlink)

    async def generate_presigned_url(self, path: str, expires: int = 300) -> str:
        raise NotImplementedError("Presigned URLs are not supported for local storage")


class S3StorageService(StorageService):
    def __init__(self) -> None:
        self.bucket = settings.S3_BUCKET
        self.base_url = settings.S3_BASE_URL.rstrip("/")
        if not self.bucket:
            raise RuntimeError("S3_BUCKET must be set when STORAGE_TYPE=s3")
        self.client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )

    async def save(self, file: UploadFile, path: str) -> str:
        content_type = file.content_type or "application/octet-stream"
        await file.seek(0)
        await asyncio.to_thread(
            self.client.upload_fileobj,
            file.file,
            self.bucket,
            path,
            ExtraArgs={"ContentType": content_type},
        )
        await file.seek(0)

        # Storage backend switching is .env-driven: local returns /files/...,
        # while S3 returns the configured CDN or bucket URL for the same path.
        if self.base_url:
            return f"{self.base_url}/{path}"
        return f"https://{self.bucket}.s3.{settings.S3_REGION}.amazonaws.com/{path}"

    async def delete(self, path: str) -> None:
        await asyncio.to_thread(
            self.client.delete_object,
            Bucket=self.bucket,
            Key=path,
        )

    async def generate_presigned_url(self, path: str, expires: int = 300) -> str:
        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": path},
            ExpiresIn=expires,
        )


def get_storage() -> StorageService:
    if settings.STORAGE_TYPE.lower() == "s3":
        return S3StorageService()
    return LocalStorageService()
