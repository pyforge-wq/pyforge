from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import StorageDriver


class LocalStorageDriver(StorageDriver):
    """Files under a root directory on the local filesystem — the default,
    and the only driver that makes sense across multiple app server
    instances without a shared filesystem (use S3/R2 there instead)."""

    def __init__(self, root: str | Path, *, base_url: str = "/storage") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def _resolve(self, path: str) -> Path:
        root = self.root.resolve()
        full = (root / path).resolve()
        if full != root and root not in full.parents:
            raise ValueError(f"Path '{path}' escapes the storage root.")
        return full

    def put(self, path: str, contents: bytes) -> None:
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(contents)

    def get(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    def delete(self, path: str) -> None:
        self._resolve(path).unlink(missing_ok=True)

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"


class S3StorageDriver(StorageDriver):
    """Backed by a real ``boto3`` S3 client. Also covers R2 and any other
    S3-compatible object store — point ``client`` at it via
    ``boto3.client("s3", endpoint_url=...)`` and set ``base_url`` for the
    right public URL shape; nothing here is AWS-specific beyond the default
    ``url()`` fallback."""

    def __init__(self, client: Any, bucket: str, *, base_url: str | None = None) -> None:
        self.client = client
        self.bucket = bucket
        self.base_url = base_url.rstrip("/") if base_url else None

    def put(self, path: str, contents: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=path, Body=contents)

    def get(self, path: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=path)
        return response["Body"].read()

    def delete(self, path: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=path)

    def exists(self, path: str) -> bool:
        import botocore.exceptions

        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except botocore.exceptions.ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey"):
                return False
            raise

    def url(self, path: str) -> str:
        if self.base_url:
            return f"{self.base_url}/{path.lstrip('/')}"
        region = self.client.meta.region_name
        return f"https://{self.bucket}.s3.{region}.amazonaws.com/{path}"
