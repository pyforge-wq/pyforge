# Storage & Cache

## Cache (`pyforge.cache`)

```python
from pyforge.cache import make_cache, set_default_cache, default_cache

set_default_cache(make_cache(config("cache")))   # in a service provider
```

```python
default_cache().put("users:1", user_dict, ttl=300)
default_cache().get("users:1")
default_cache().forget("users:1")
default_cache().remember("users:1", 300, lambda: User.find(1).to_dict())
default_cache().flush()
```

Drivers, selected via `config("cache")`:

| Driver | Notes |
|---|---|
| `MemoryCacheDriver` (default) | In-process, gone on restart |
| `FileCacheDriver` | Pickled files on disk, survives a restart |
| `RedisCacheDriver` | Needs `pip install "pyforge-framework[cache]"`. `.flush()` runs `FLUSHDB` — use a **dedicated Redis DB index** for the cache so flushing it doesn't wipe something else sharing that instance |

```bash
pyforge cache:clear
```

!!! danger "Redis cache/queue and the `pickle` trust boundary"
    `RedisCacheDriver` (and `RedisQueueDriver`) use `pickle.dumps`/
    `pickle.loads` to store arbitrary Python values — standard practice for
    an app's own, private cache/queue backend. But `pickle.loads` on data
    from a Redis instance you don't fully control is a remote-code-execution
    risk, not just a data-integrity one. Point `REDIS_URL` at a private
    instance only your own application writes to. See
    [Security](security.md#secret-management).

## Storage (`pyforge.storage`)

```python
from pyforge.storage import make_storage, set_default_storage, default_storage

set_default_storage(make_storage(config("storage")))   # in a service provider
```

```python
default_storage().put("avatars/photo.jpg", file_bytes)
default_storage().get("avatars/photo.jpg")
default_storage().url("avatars/photo.jpg")
default_storage().exists("avatars/photo.jpg")
default_storage().delete("avatars/photo.jpg")
```

Drivers, selected via `config("storage")`:

| Driver | Notes |
|---|---|
| `LocalStorageDriver` (default) | Rejects paths that escape its configured root (path-traversal check) |
| `S3StorageDriver` | Needs `pip install "pyforge-framework[storage]"`. Also covers R2 and other S3-compatible stores via `endpoint_url` + a custom `base_url` |

No dedicated Azure Blob/GCS drivers exist yet.

!!! warning "File upload validation is not built"
    FastAPI's native `UploadFile` (size via `Content-Length`, `content_type`
    inspection) is directly usable, but PyForge doesn't add a
    validation-rule layer on top of it — there's no
    `"file|max:2048|mimes:jpg,png"`-style rule in `FormRequest` yet. Validate
    size and content type yourself before calling `Storage.put(...)`; the
    drivers write whatever bytes they're given, with no restriction of their
    own beyond the local driver's path-traversal check.
