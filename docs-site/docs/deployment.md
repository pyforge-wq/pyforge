# Deployment

Every `pyforge new` project includes a `Dockerfile` and `.dockerignore` at
its root — ready to build once `pyforge-framework` is published (or with a
locally built wheel today; see below).

## The generated Dockerfile

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY . .
RUN pip install .

RUN useradd --create-home --uid 1000 app \
    && mkdir -p storage \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

A few decisions worth knowing about:

- **`build-essential` is there for `bcrypt`**, a transitive dependency of the
  `auth` extra — it ships C extensions and `python:3.11-slim` has no
  compiler by default. Drop this layer if your project doesn't use
  `pyforge.auth`.
- **Runs as a non-root `app` user.** `storage/` is created and `chown`ed
  before the switch, since the app writes to it (SQLite files, local
  storage driver, cache files).
- **Migrations are not run at container startup**, deliberately — a rolling
  deploy starting N replicas would otherwise race N concurrent
  `alembic upgrade head` calls against the same database. Run
  `pyforge migrate` as its own step in your deploy pipeline instead.

### Building it

```bash
docker build -t my-app .
docker run -d -p 8000:8000 --env-file .env my-app
```

!!! note "Before `pyforge-framework` is on PyPI"
    Until the package is published, `pip install .` inside the Docker build
    can't resolve `pyforge-framework` from the network. Build a local wheel
    of the framework and add it as an earlier layer:

    ```bash
    python -m build --wheel --outdir dist /path/to/pyforge
    cp dist/pyforge_framework-*.whl .
    ```

    ```dockerfile
    COPY pyforge_framework-*.whl ./
    RUN pip install pyforge_framework-*.whl
    RUN pip install .
    ```

    This is exactly what the framework's own CI does to verify the
    Dockerfile template end-to-end before every release.

## Environment configuration in production

`.env` is never baked into the image (`.dockerignore` excludes it) and
should never be. Set real values through your platform's environment
variables/secrets instead:

- **`JWT_SECRET`** — generate a *different* one for production than your
  local `.env`'s (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).
- **`DATABASE_URL`** / the individual `DB_*` vars — point at your real
  database, not the generated SQLite default.
- **`REDIS_URL`** — if using the Redis cache/queue drivers, point at a
  private instance only your app writes to (see [Security](security.md#redis-and-the-pickle-trust-boundary)).
- **`APP_DEBUG=false`** — must be false in production; it gates whether
  exception detail leaks into error responses.

## Platform recipes

- **Fly.io / Render / Railway** — point the platform at the repo and let it
  build the Dockerfile directly. Add `pyforge migrate` as a release/pre-deploy
  command if the platform supports one; otherwise run it manually against
  the production database after a deploy that includes a migration.
- **A single VM (systemd + Docker)** — `docker run --restart unless-stopped`,
  a reverse proxy (Caddy/nginx) in front for TLS, `pyforge migrate` run by
  hand or from a deploy script before restarting the container.
- **Kubernetes** — the generated Dockerfile is a normal Deployment image; run
  `pyforge migrate` as a `Job` (or an `initContainer` on a single canary
  replica) gated to complete before the rollout, for the same
  concurrent-migration reason above.

## Verifying it works

Before trusting any of this in production, prove it locally:

```bash
docker build -t my-app .
docker run -d -p 8000:8000 --name my-app-test my-app
curl http://localhost:8000/
docker logs my-app-test
docker stop my-app-test && docker rm my-app-test
```
