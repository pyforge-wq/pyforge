"""File storage — an *optional* module (``pyforge.storage``), not imported
by ``import pyforge``. The S3 driver (also covers R2 and other
S3-compatible stores) needs the ``storage`` extra:
``pip install pyforge-framework[storage]``.

    from pyforge.storage import Storage, make_storage, set_default_storage
"""

from .base import StorageDriver
from .defaults import default_storage, set_default_storage
from .drivers import LocalStorageDriver, S3StorageDriver
from .storage import Storage, make_storage

__all__ = [
    "LocalStorageDriver",
    "S3StorageDriver",
    "Storage",
    "StorageDriver",
    "default_storage",
    "make_storage",
    "set_default_storage",
]
