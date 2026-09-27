# Events, Queues & Scheduling

Three independent, optional modules — none imported by `import pyforge`.
Each follows the same shape: a `make_x(config)` factory reading the
matching `config/x.py`, plus `set_default_x(...)`/`default_x()` for the
process-wide instance a service provider registers once.

## Events (`pyforge.events`)

```python
from pyforge.events import event, listen, Listener

class UserRegistered:
    def __init__(self, user) -> None:
        self.user = user

class SendWelcomeEmail(Listener):
    async def handle(self, evt: UserRegistered) -> None:
        mail().to(evt.user.email).send(WelcomeEmail(evt.user))

listen(UserRegistered, SendWelcomeEmail)   # typically in a service provider's boot()
await event(UserRegistered(user))
```

!!! note "`event(...)` is `await`-able"
    Unlike a sync-looking dispatch call in some other frameworks, `event(...)`
    must be awaited — dispatch always happens from already-`async def` code,
    and listeners are legitimately `async def` too, so this is the honest
    shape rather than reaching for `asyncio.run()` (which breaks inside an
    already-running event loop). Both sync and async `handle()` methods work
    as listeners.

## Queues & jobs (`pyforge.queue`)

```python
from pyforge.queue import Job, dispatch, make_queue, set_default_queue

class SendWelcomeEmail(Job):
    max_retries = 2
    retry_backoff_seconds = 5

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    def handle(self) -> None:
        user = User.find(self.user_id)
        mail().to(user.email).send(WelcomeEmail(user))

set_default_queue(make_queue(config("queue")))   # in a service provider
dispatch(SendWelcomeEmail(user.id))
```

```bash
pyforge queue:work --queue=high,default --max-jobs 100 --timeout 5
```

- **`SyncQueueDriver`** (the default) runs jobs immediately — nothing to
  work through, useful in dev/tests without standing up Redis.
- **`RedisQueueDriver`** needs `pip install "pyforge-framework[queue]"` —
  `BLPOP` across queue names in priority order.

!!! warning "A `Job` must be picklable"
    Only plain attributes — no open file handles, sessions, or connections.
    Pickling means the *worker* process runs a byte-for-byte copy of the
    instance you pushed: its attributes are captured **by value** at
    dispatch time, so a job can't report results back to the dispatching
    process via a shared list/object. Write results to the database (or
    another out-of-band store) instead. See
    [Troubleshooting](troubleshooting.md#a-jobs-side-effects-dont-show-up-in-my-test)
    for the exact symptom this causes in tests.

`Worker` retries a failing job up to `max_retries` times (sleeping
`retry_backoff_seconds` between attempts). Pass an `on_failure` callback to
observe a job that exhausted its retries:

```python
from pyforge.queue import Worker

def log_failure(job, exc: Exception) -> None:
    logger.error("Job failed permanently: %s (%s)", job, exc)

worker = Worker(driver, on_failure=log_failure)
```

No job-timeout enforcement is built — there's no reliable, portable way to
hard-kill a stuck synchronous job without real subprocess isolation.

### Generate one

```bash
pyforge make:job SendWelcomeEmail
```

## Scheduler (`pyforge.scheduler`)

```python
# app/schedule.py
from pyforge.scheduler import Schedule

schedule = Schedule()
schedule.every_day(GenerateReports()).at("02:00")
schedule.every_hour(CleanupTemporaryFiles())
schedule.every_minute(PollExternalQueue())
schedule.cron("*/15 * * * *", SyncExternalData())
```

```bash
pyforge schedule:run
```

`schedule:run` runs every currently-due task **once and exits** — meant to
be invoked by a real OS cron entry every minute, the same model as any
cron-driven task scheduler:

```cron
* * * * * cd /path/to/app && /path/to/venv/bin/pyforge schedule:run
```

There's no persisted "last run" state — the once-a-minute external cadence
plus each task's own time check is sufficient, and this is why the
scheduler is stateless by design. A "job" here just needs a `handle()`
method or to be callable. `schedule:run` wraps execution in a database
session automatically if `config/database.py` exists.

### Generate an event/listener

```bash
pyforge make:event UserRegistered
pyforge make:listener SendWelcomeEmail
```

## Testing without real infrastructure

See [Testing](testing.md) for `fake_events()` and `fake_queue()` — recording
fakes that let you assert an event was dispatched or a job was pushed
without actually running listeners or executing jobs.
