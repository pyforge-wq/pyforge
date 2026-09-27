"""Caching — an *optional* module (``pyforge.cache``), not imported by
``import pyforge``. The Redis driver needs the ``cache`` extra:
``pip install pyforge-framework[cache]``.

    from pyforge.cache import Cache, make_cache, set_default_cache
"""

from .base import CacheDriver
from .cache import Cache, make_cache
from .defaults import default_cache, set_default_cache
from .drivers import FileCacheDriver, MemoryCacheDriver, RedisCacheDriver

__all__ = [
    "Cache",
    "CacheDriver",
    "FileCacheDriver",
    "MemoryCacheDriver",
    "RedisCacheDriver",
    "default_cache",
    "make_cache",
    "set_default_cache",
]
