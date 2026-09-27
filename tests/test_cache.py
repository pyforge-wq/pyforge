import time

import fakeredis
import pytest

from pyforge.cache import (
    Cache,
    FileCacheDriver,
    MemoryCacheDriver,
    RedisCacheDriver,
    default_cache,
    make_cache,
    set_default_cache,
)


@pytest.fixture(params=["memory", "file", "redis"])
def cache(request, tmp_path) -> Cache:
    if request.param == "memory":
        return Cache(MemoryCacheDriver())
    if request.param == "file":
        return Cache(FileCacheDriver(tmp_path / "cache"))
    return Cache(RedisCacheDriver(fakeredis.FakeRedis()))


def test_put_and_get(cache: Cache) -> None:
    cache.put("key", {"a": 1})
    assert cache.get("key") == {"a": 1}


def test_get_missing_returns_default(cache: Cache) -> None:
    assert cache.get("missing") is None
    assert cache.get("missing", "fallback") == "fallback"


def test_forget(cache: Cache) -> None:
    cache.put("key", "value")
    cache.forget("key")
    assert cache.get("key") is None


def test_flush(cache: Cache) -> None:
    cache.put("a", 1)
    cache.put("b", 2)
    cache.flush()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_ttl_expires(cache: Cache) -> None:
    cache.put("key", "value", ttl=1)
    assert cache.get("key") == "value"
    time.sleep(1.2)
    assert cache.get("key") is None


def test_remember_calls_callback_only_once(cache: Cache) -> None:
    calls = []

    def build() -> str:
        calls.append(1)
        return "computed"

    assert cache.remember("key", 60, build) == "computed"
    assert cache.remember("key", 60, build) == "computed"
    assert len(calls) == 1


def test_make_cache_memory() -> None:
    cache = make_cache({"default": "memory"})
    assert isinstance(cache.driver, MemoryCacheDriver)


def test_make_cache_file(tmp_path) -> None:
    cache = make_cache({"default": "file", "file_path": str(tmp_path / "cache")})
    assert isinstance(cache.driver, FileCacheDriver)


def test_make_cache_unknown_driver_raises() -> None:
    with pytest.raises(ValueError):
        make_cache({"default": "not-a-driver"})


def test_default_cache_roundtrip() -> None:
    cache = Cache(MemoryCacheDriver())
    set_default_cache(cache)
    try:
        assert default_cache() is cache
    finally:
        import pyforge.cache.defaults as defaults_module

        defaults_module._default_cache = None


def test_default_cache_raises_when_unset() -> None:
    import pyforge.cache.defaults as defaults_module

    defaults_module._default_cache = None
    with pytest.raises(RuntimeError):
        default_cache()
