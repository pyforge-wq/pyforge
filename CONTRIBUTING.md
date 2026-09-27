# Contributing to PyForge

Thanks for considering a contribution. PyForge is at `0.7.0`, all 7 roadmap
phases implemented but still pre-`1.0.0` — see
[docs/architecture/09-roadmap.md](docs/architecture/09-roadmap.md) for what's
built and what's next before starting significant work, and consider opening
an issue to discuss direction first for anything beyond a small fix.

## Development setup

```bash
git clone https://github.com/pyforge-framework/pyforge.git
cd pyforge
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Ground rules

These come directly from the project's own design principles
([docs/architecture/01-framework-architecture.md](docs/architecture/01-framework-architecture.md)):

1. **Every public API needs a test and a docs entry**, in the same PR. See
   [docs/architecture/08-documentation-architecture.md#docs-as-code-rules](docs/architecture/08-documentation-architecture.md#docs-as-code-rules).
2. **Core stays small.** Before adding a feature, ask "does this belong in
   core, or should it be a `pyforge-*` package?" — see
   [docs/architecture/02-core-package-architecture.md](docs/architecture/02-core-package-architecture.md)
   for the test to apply, and raise it in your PR description if it's not
   obvious which side a feature falls on.
3. **Never hide FastAPI.** Any change that makes a native FastAPI/Starlette
   feature (middleware, dependencies, responses, sub-routers) stop working
   inside a PyForge app is a regression, not a trade-off.
4. **No speculative abstraction.** Don't add configuration options,
   plugin hooks, or base classes for a use case that doesn't exist yet — see
   the "no premature abstraction" note in
   [docs/architecture/05-plugin-package-architecture.md](docs/architecture/05-plugin-package-architecture.md#what's-designed-but-not-automatic-yet)
   for an example of a deliberately deferred feature.
5. **Don't claim unbuilt features in docs.** If you're implementing part of
   a roadmap phase, update [docs/architecture/09-roadmap.md](docs/architecture/09-roadmap.md)'s
   checklist in the same PR.

## Code style

- Python 3.11+, fully type-hinted.
- `ruff check` and `mypy` must pass (`pip install -e ".[dev]"` installs
  both); CI enforces this.
- Prefer explicit, readable code over metaprogramming — if a `getattr`/`setattr`
  trick can be replaced with a plain method or property, prefer the plain
  version.

## Tests

```bash
pytest                      # framework's own test suite
```

New framework-level behavior (container, config, routing, application core)
gets a test in `tests/`, following the existing files' pattern of testing
against real objects (a real `Container()`, a real
`fastapi.testclient.TestClient`) rather than mocks. Changes to the project
generator (`src/pyforge/console/stubs/`) should be validated by actually
running `pyforge new` against a temp directory and confirming the result
imports and serves — see the CI workflow for the exact commands.

## Commit messages / PRs

- Keep PRs focused; unrelated cleanup belongs in its own PR.
- Explain *why*, not just *what*, in the PR description — the same standard
  the architecture docs hold themselves to.

## Reporting bugs / requesting features

Use [GitHub Issues](https://github.com/pyforge-framework/pyforge/issues).
For security vulnerabilities, see [SECURITY.md](SECURITY.md) instead of
opening a public issue.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
