# Documentation Architecture

## Two audiences, two locations

- **`docs/architecture/`** (this directory): internal design documentation —
  why the framework is shaped the way it is, what's implemented vs. planned,
  the contract between core and packages. Written for framework
  contributors and for anyone deciding whether to depend on PyForge. Lives
  in-repo, in Markdown, reviewed like code (a design change gets a diff
  here).
- **`docs-site/`** (built — see
  [09-roadmap.md](09-roadmap.md#phase-7--production-readiness--070-except-where-noted)):
  task-oriented guides for people *using* PyForge to build an app —
  installation, quick start, routing, controllers, models, migrations,
  validation, auth, middleware, DI, events, queues, jobs, scheduling, cache,
  storage, mail, notifications, tenancy, testing, security, deployment, CLI
  reference, packages, troubleshooting, contributing. Built with MkDocs +
  Material (search, dark mode, mobile layout), run locally with
  `mkdocs serve` from `docs-site/`, built with `mkdocs build --strict` in
  CI so a broken internal link fails the same way a broken test would. Every
  code sample matches something exercised in `tests/` or the generated
  project template — same rule as this directory, just aimed at a different
  reader. Not yet deployed to a public URL (e.g. GitHub Pages) — that's a
  separate, human-triggered decision, the same reasoning as PyPI publishing
  in [09-roadmap.md](09-roadmap.md).

## Docs-as-code rules

1. **No undocumented public API.** Every symbol exported from
   `pyforge/__init__.py` has an entry in
   [03-public-api-design.md](03-public-api-design.md) with a signature and a
   runnable example, and a corresponding test in `tests/`. A PR adding a
   public symbol without both is incomplete, not just "missing docs."
2. **No claiming unbuilt features.** Anything not implemented is either
   absent from the docs entirely or explicitly marked against
   [09-roadmap.md](09-roadmap.md) (e.g. "Status: design only — nothing in
   this document is implemented yet," as in
   [06-database-architecture.md](06-database-architecture.md)). This is the
   single most important rule in this file: a framework's docs are the
   product's first impression, and a doc that oversells what exists is worse
   than no doc.
3. **Examples run.** Every code block in `docs/architecture/*.md` or
   `docs-site/docs/*.md` describing *implemented* behavior corresponds to
   something exercised in `tests/` or in the generated-project template
   (`src/pyforge/console/stubs/`) — not hand-typed and hoped-correct.
4. **Docs move with the code.** A PR that changes a public signature updates
   the matching doc in the same commit; docs are not a follow-up task.

## Versioning

Documentation versions with the code, not separately — `docs/architecture/`
and `docs-site/` at a given git tag both describe that release, consistent
with [CHANGELOG.md](../../CHANGELOG.md). `docs-site/` doesn't yet have its
own version selector (no `mike`-based versioned deploys) — that's only worth
adding once a public deployment exists and more than one version needs to
stay browsable at once.

## Style

- Prefer a table over prose when documenting a fixed set of options/members
  (see how [03-public-api-design.md](03-public-api-design.md) documents
  `PyForge`'s members).
- Prefer a runnable code block over a description of what code would do.
- State trade-offs explicitly (why core vs. package, why one design over an
  alternative) rather than presenting the current design as the only
  possible one — future contributors need the reasoning, not just the
  conclusion, especially for decisions the roadmap marks as still open.
