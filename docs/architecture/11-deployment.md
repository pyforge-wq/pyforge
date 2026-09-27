# Deployment

How a generated PyForge project actually gets to production. This document
covers the Docker image `pyforge new` generates, environment configuration,
and recipes for common platforms — see [09-roadmap.md](09-roadmap.md) for
what's still not built (a hosted docs site would eventually carry an
end-user version of this page; until then, this is it).

## The generated Dockerfile

Every `pyforge new <name>` project includes a `Dockerfile` and
`.dockerignore` at its root. It's a single-stage `python:3.11-slim` build:

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
...
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY . .
RUN pip install .

RUN useradd --create-home --uid 1000 app && mkdir -p storage && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

A few decisions worth calling out:

- **`build-essential` is installed for one reason**: `bcrypt` (a transitive
  dependency of the `auth` extra) ships C extensions, and `python:3.11-slim`
  has no compiler by default. If your project doesn't use `pyforge.auth`,
  you can drop this layer — it's not needed for anything else in the
  framework.
- **Runs as a non-root `app` user (uid 1000).** `storage/` is created and
  `chown`ed before the `USER app` switch, since the app needs to write to it
  (SQLite files, the local storage driver, cache files) and a
  container-created directory is root-owned by default.
- **`pip install .` needs a real `pyforge-framework` to resolve.** This only
  works once `pyforge-framework` is actually published to PyPI (see
  [09-roadmap.md](09-roadmap.md) — publishing is prepared but not yet done).
  Until then, building this Dockerfile for a generated project requires
  either a local wheel installed as an earlier layer
  (`COPY pyforge_framework-*.whl ./` + `RUN pip install ./pyforge_framework-*.whl`
  before `RUN pip install .`) or a `--find-links` pointed at a local wheel
  directory. This exact scenario is what CI's `docker-smoke-test` job
  exercises (see below) — it's how the Dockerfile template itself is
  verified to actually build and serve a request, not just look plausible.
- **Migrations are not run at container startup**, deliberately. A rolling
  deploy that starts N replicas of this image would otherwise race N
  concurrent `alembic upgrade head` calls against the same database. Run
  `pyforge migrate` as its own step in your deploy pipeline — a release
  phase command (Heroku/Render), an init container (Kubernetes), or a
  one-off task (ECS) — before traffic shifts to the new version.

### Building and running it locally

Once `pyforge-framework` is on PyPI, this is the whole story:

```bash
docker build -t my-app .
docker run -d -p 8000:8000 --env-file .env my-app
```

Before that, build a local wheel of the framework and install it as an
extra layer (this is exactly what was hand-verified while writing this
doc — a real image was built and a real `curl` against it returned `200`):

```bash
python -m build --wheel --outdir /tmp/pyforge_dist /path/to/pyforge
cp /tmp/pyforge_dist/pyforge_framework-*.whl .
```

then add a layer before `RUN pip install .`:

```dockerfile
COPY pyforge_framework-*.whl ./
RUN pip install pyforge_framework-*.whl
```

## Environment configuration in production

Generated projects load config through `config/*.py` → `env(...)` →
`.env`/real process environment (see
[03-public-api-design.md](03-public-api-design.md)). `.env` is
`.gitignore`d from project creation; it never ships inside the Docker image
(`.dockerignore` excludes it explicitly) and never should. Set real values
through whatever your platform calls environment variables/secrets:

- `JWT_SECRET` — `pyforge new` already generates a random one into your
  local `.env` (`secrets.token_urlsafe(32)`); generate a **different** one
  for production and set it as a platform secret, not a copy of the dev
  value.
- `DATABASE_URL` / the individual `DB_*` vars — point at your real database,
  not the generated SQLite default.
- `REDIS_URL` — if using the Redis cache/queue drivers, point at a private
  instance your application alone writes to (see
  [10-security.md](10-security.md)'s note on the `pickle` deserialization
  trust boundary — this is a hard requirement, not a suggestion).
- `APP_DEBUG` — must be `false` in production; `config("app.debug")` gates
  whether exception detail is included in the centralized error → HTTP
  response mapping (see [03-public-api-design.md](03-public-api-design.md)).

## Platform recipes

These are deliberately short — each platform already has excellent generic
"deploy a Dockerfile" docs, and PyForge doesn't need platform-specific
tooling beyond what's already generated.

- **Fly.io / Render / Railway**: point the platform at the repo, let it
  build the generated `Dockerfile` directly. Add `pyforge migrate` as a
  release/pre-deploy command if the platform supports one; otherwise run it
  manually against the production database after each deploy that includes
  a migration.
- **A single VM (systemd + Docker)**: `docker run` with a restart policy
  (`--restart unless-stopped`), a reverse proxy (Caddy/nginx) in front for
  TLS, `pyforge migrate` run by hand or from a deploy script before
  restarting the container.
- **Kubernetes**: the generated Dockerfile is a normal Deployment image; run
  `pyforge migrate` as a `Job` (or an `initContainer` on a single canary
  replica) gated to complete before the Deployment rolls out, for the same
  concurrent-migration reason described above.

## What CI verifies

The `docker-smoke-test` job in `.github/workflows/ci.yml` generates a fresh
project, builds a real framework wheel, builds the generated `Dockerfile`
(with the local-wheel layer described above), runs the resulting image, and
`curl`s the root endpoint expecting a real `200`. This exists because the
first version of the generated `pyproject.toml.stub` shipped with no
`[tool.hatch.build.targets.wheel]` configuration — `pip install .` failed
for *every* freshly generated project (hatchling couldn't determine what to
package for a flat-layout application, not a `<name>/` package directory),
and nothing in the existing test suite or the pre-existing
`generated-project-smoke-test` CI job ever actually built the Dockerfile or
ran `pip install .` against a generated project's own `pyproject.toml`, so
it went unnoticed until this Docker verification pass. The fix was adding
`bypass-selection = true` to that table (tells hatchling this
`pyproject.toml` exists to declare dependencies, not to ship a wheel of its
own). The `docker-smoke-test` job is what keeps this specific class of
regression from reappearing silently.
