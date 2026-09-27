# PyForge

**A batteries-included web framework for Python — built on FastAPI.**

PyForge gives you an elegant project structure, a capable CLI, routing,
controllers, a DI container, and service providers out of the box, while
FastAPI stays the real HTTP engine underneath — always one attribute away
(`app.fastapi`), never hidden.

!!! info "Status"
    `0.7.0` — all 7 roadmap phases implemented and tested, still pre-`1.0.0`
    on purpose. See [the roadmap](https://github.com/pyforge-wq/pyforge/blob/main/docs/architecture/09-roadmap.md)
    for exactly what's built vs. deferred.

## Install it and run something in under a minute

```bash
pip install pyforge-framework
pyforge new blog
cd blog
pyforge serve
```

Visit `http://localhost:8000/` for a welcome message, or
`http://localhost:8000/docs` for FastAPI's interactive API docs — generated
automatically, for free.

Next: [Getting Started](getting-started.md) walks through this in more
detail and builds a small real endpoint.

## Why PyForge exists

FastAPI is an excellent HTTP layer with a thin story around everything
*around* the HTTP layer: how you structure a growing app, wire dependencies,
organize config, or generate boilerplate. PyForge answers those questions
directly, in idiomatic, typed Python — a real project structure, a DI
container, service providers, and a code generator, built as proper Python
architecture rather than borrowed wholesale from another language's
framework.

Four levels of usage stay available at once, always:

| Level | Example | What's happening |
|---|---|---|
| Beginner | `User.create(...)` / `router.get("/users", UserController.index)` | Convention: container-resolved controllers, an Active-Record `Model`, no manual wiring. |
| Intermediate | `User.query().where(...).paginate(...)` | Explicit query building, still declarative. |
| Advanced | `container.make(CheckoutService)`, a real `sqlalchemy.orm.Session` | Direct container/SQLAlchemy use, custom bindings. |
| FastAPI expert | `app.fastapi.add_middleware(...)`, `Depends(...)`, raw `session.execute(...)` | Drop to FastAPI/Starlette/SQLAlchemy directly — nothing is hidden. |

## Find your way around

- **New to PyForge?** Start with [Getting Started](getting-started.md), then
  [Routing & Controllers](routing-and-controllers.md) and
  [Database & ORM](database.md).
- **Adding a feature?** Jump straight to the guide for it — Auth, Queues,
  Mail, Storage, Cache, Multi-tenancy, and Testing each have their own page
  in the sidebar.
- **Shipping to production?** [Security](security.md) and
  [Deployment](deployment.md) cover the hardening pass and the generated
  Docker image.
- **Something broken?** [Troubleshooting](troubleshooting.md) covers the
  gotchas that actually trip people up (most of them: a controller class
  defined inside a function, or an import-order issue with `@role`).

## What's real, what isn't

Every code sample in this site is backed by a passing test in the framework's
own `tests/` directory or exercised by the generated project template — none
of it is aspirational. Where something isn't built yet (route-model binding,
job timeouts, an admin UI, OAuth2 as a full provider), the relevant guide
says so directly instead of staying quiet about it.

## Getting help

- Found a bug or have a feature request? Open an issue on
  [GitHub](https://github.com/pyforge-wq/pyforge/issues).
- Security issue? See [SECURITY.md](https://github.com/pyforge-wq/pyforge/blob/main/SECURITY.md)
  for how to report it privately rather than as a public issue.
- Want to contribute? See [Contributing](contributing.md).
