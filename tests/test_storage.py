import boto3
import pytest
from moto import mock_aws

from pyforge.storage import (
    LocalStorageDriver,
    S3StorageDriver,
    Storage,
    default_storage,
    make_storage,
    set_default_storage,
)


def test_local_driver_put_get_delete_exists(tmp_path) -> None:
    driver = LocalStorageDriver(tmp_path)
    storage = Storage(driver)

    assert storage.exists("avatars/photo.jpg") is False
    storage.put("avatars/photo.jpg", b"binary-data")
    assert storage.exists("avatars/photo.jpg") is True
    assert storage.get("avatars/photo.jpg") == b"binary-data"

    storage.delete("avatars/photo.jpg")
    assert storage.exists("avatars/photo.jpg") is False


def test_local_driver_accepts_str_contents(tmp_path) -> None:
    storage = Storage(LocalStorageDriver(tmp_path))
    storage.put("notes/hello.txt", "hello world")
    assert storage.get("notes/hello.txt") == b"hello world"


def test_local_driver_url(tmp_path) -> None:
    storage = Storage(LocalStorageDriver(tmp_path, base_url="/files"))
    assert storage.url("avatars/photo.jpg") == "/files/avatars/photo.jpg"


def test_local_driver_rejects_path_traversal(tmp_path) -> None:
    storage = Storage(LocalStorageDriver(tmp_path))
    with pytest.raises(ValueError):
        storage.put("../../etc/passwd", b"pwned")


def test_make_storage_local(tmp_path) -> None:
    storage = make_storage({"default": "local", "root": str(tmp_path), "base_url": "/storage"})
    assert isinstance(storage.driver, LocalStorageDriver)


def test_make_storage_unknown_driver_raises() -> None:
    with pytest.raises(ValueError):
        make_storage({"default": "not-a-driver"})


def test_default_storage_roundtrip(tmp_path) -> None:
    storage = Storage(LocalStorageDriver(tmp_path))
    set_default_storage(storage)
    try:
        assert default_storage() is storage
    finally:
        import pyforge.storage.defaults as defaults_module

        defaults_module._default_storage = None


@pytest.fixture
def s3_bucket():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")
        yield client


def test_s3_driver_put_get_delete_exists(s3_bucket) -> None:
    driver = S3StorageDriver(s3_bucket, "test-bucket")
    storage = Storage(driver)

    assert storage.exists("avatars/photo.jpg") is False
    storage.put("avatars/photo.jpg", b"binary-data")
    assert storage.exists("avatars/photo.jpg") is True
    assert storage.get("avatars/photo.jpg") == b"binary-data"

    storage.delete("avatars/photo.jpg")
    assert storage.exists("avatars/photo.jpg") is False


def test_s3_driver_default_url(s3_bucket) -> None:
    driver = S3StorageDriver(s3_bucket, "test-bucket")
    assert driver.url("avatars/photo.jpg") == "https://test-bucket.s3.us-east-1.amazonaws.com/avatars/photo.jpg"


def test_s3_driver_custom_base_url_for_r2_style_endpoints(s3_bucket) -> None:
    driver = S3StorageDriver(s3_bucket, "test-bucket", base_url="https://cdn.example.com")
    assert driver.url("avatars/photo.jpg") == "https://cdn.example.com/avatars/photo.jpg"


def test_make_storage_s3(s3_bucket, monkeypatch) -> None:
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    storage = make_storage({"default": "s3", "bucket": "test-bucket"})
    assert isinstance(storage.driver, S3StorageDriver)
    storage.put("hello.txt", "hi")
    assert storage.get("hello.txt") == b"hi"
