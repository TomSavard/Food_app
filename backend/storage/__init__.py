"""Storage service abstraction for recipe images.

Implements a pluggable storage backend so we can swap S3 providers
(Neon Object Storage, Cloudflare R2, AWS S3) without changing business logic.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PresignedUrlResponse:
    upload_url: str
    object_key: str


@dataclass
class DeleteResult:
    success: bool
    error: Optional[str] = None


class StorageService(ABC):
    """Abstract storage backend for recipe images."""

    ALLOWED_CONTENT_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}
    MAX_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB


    @abstractmethod
    def generate_presigned_put_url(
        self, object_key: str, content_type: str, size_bytes: int
    ) -> PresignedUrlResponse:
        """Generate a presigned URL for uploading an object."""
        ...

    @abstractmethod
    def delete_object(self, object_key: str) -> DeleteResult:
        """Delete an object from storage."""
        ...

    def validate_upload(
        self, content_type: str, size_bytes: int
    ) -> tuple[bool, Optional[str]]:
        """Validate a proposed upload. Returns (is_valid, error_message)."""
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            return False, f"Type {content_type} non supporté"
        if size_bytes > self.MAX_SIZE_BYTES:
            return False, f"Taille maximale: {self.MAX_SIZE_BYTES // 1024 // 1024} Mo"
        return True, None


class NeonStorageService(StorageService):
    """Neon Object Storage implementation (S3-compatible).

    Env vars (produced by `neon deploy` or `neon credentials create`):
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        AWS_ENDPOINT_URL_S3, AWS_REGION
        AWS_S3_BUCKET
    """

    def __init__(self) -> None:
        import boto3

        self.bucket: str = os.getenv("AWS_S3_BUCKET", "")
        self.endpoint: str = os.getenv("AWS_ENDPOINT_URL_S3", "")
        self.access_key: str = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")

        if not all([self.bucket, self.endpoint, self.access_key, self.secret_key]):
            raise RuntimeError(
                "AWS_S3_BUCKET, AWS_ENDPOINT_URL_S3, AWS_ACCESS_KEY_ID, "
                "AWS_SECRET_ACCESS_KEY environment variables required"
            )

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=boto3.session.Config(s3={"use_accelerate_endpoint": False}),
        )

    def generate_presigned_put_url(
        self, object_key: str, content_type: str, size_bytes: int
    ) -> PresignedUrlResponse:
        url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": object_key,
                
            },
            ExpiresIn=3600,  # 1 hour
        )
        return PresignedUrlResponse(
            upload_url=url,
            object_key=object_key,
        )

    async def upload_file(self, file, object_key: str, content_type: str) -> None:
        self._client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=file,
            ContentType=content_type,
        )

    def delete_object(self, object_key: str) -> DeleteResult:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=object_key)
            return DeleteResult(success=True)
        except Exception as e:
            return DeleteResult(success=False, error=str(e))


def get_storage_service() -> StorageService:
    """Factory: returns the configured storage service."""
    return NeonStorageService()
