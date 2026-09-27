"""Queue / jobs — an *optional* module (``pyforge.queue``), not imported by
``import pyforge``. The Redis driver needs the ``queue`` extra:
``pip install pyforge-framework[queue]``.

    from pyforge.queue import Job, dispatch, make_queue, set_default_queue
"""

from .drivers import QueueDriver, RedisQueueDriver, SyncQueueDriver
from .job import Job
from .queue import default_queue, dispatch, make_queue, set_default_queue
from .worker import Worker

__all__ = [
    "Job",
    "QueueDriver",
    "RedisQueueDriver",
    "SyncQueueDriver",
    "Worker",
    "default_queue",
    "dispatch",
    "make_queue",
    "set_default_queue",
]
