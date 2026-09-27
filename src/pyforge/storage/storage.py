from __future__ import annotations

from typing import Any

from .base import StorageDriver
from .drivers import LocalStorageDriver, S3StorageDriver


class Storage:
    """``Storage.put("avatars/photo.jpg", data)`` / ``.get(...)`` /
    ``.delete(...)`` / ``.url(...)`` / ``.exists(...)`` over whichever
    :class:`StorageDriver` was configured."""

    def __init__(self, driver: StorageDriver) -> None:
        self.driver = driver

    def put(self, path: str, contents: bytes | str) -> None:
        if isinstance(contents, str):
            contents = contents.encode("utf-8")
        self.driver.put(path, contents)

    def get(self, path: str) -> bytes:
        return self.driver.get(path)

    def delete(self, path: str) -> None:
        self.driver.delete(path)

    def exists(self, path: str) -> bool:
        return self.driver.exists(path)

    def url(self, path: str) -> str:
        return self.driver.url(path)


def make_storage(config: dict[str, Any]) -> Storage:
    """Builds a :class:`Storage` from the same shape as a generated
    project's ``config/storage.py``."""
    driver_name = config.get("default", "local")

    if driver_name == "local":
        return Storage(
            LocalStorageDriver(config.get("root", "storage/app"), base_url=config.get("base_url", "/storage"))
        )

    if driver_name == "s3":
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=config.get("endpoint_url"),
            aws_access_key_id=config.get("access_key_id"),
            aws_secret_access_key=config.get("secret_access_key"),
            region_name=config.get("region"),
        )
        return Storage(S3StorageDriver(client, config["bucket"], base_url=config.get("base_url")))

    raise ValueError(f"Unknown storage driver '{driver_name}'.")
