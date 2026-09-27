# Contributing

PyForge is at `0.7.0` — all 7 roadmap phases implemented, still pre-`1.0.0`.
See the [roadmap](https://github.com/pyforge-framework/pyforge/blob/main/docs/architecture/09-roadmap.md)
for what's built vs. planned before starting significant work, and consider
opening an issue to discuss direction first for anything beyond a small fix.

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

1. **Every public API needs a test and a docs entry**, in the same PR.
2. **Core stays small.** Before adding a feature, ask "does this belong in
   core, or should it be a `pyforge-*` package?" — see
   [Extending PyForge](packages.md).
3. **Never hide FastAPI.** Any change that breaks a native
   FastAPI/Starlette feature (middleware, dependencies, responses,
   sub-routers) inside a PyForge app is a regression, not a trade-off.
4. **No speculative abstraction.** Don't add configuration options, plugin
   hooks, or base classes for a use case that doesn't exist yet.
5. **Don't claim unbuilt features in docs.** If you're implementing part of
   a roadmap phase, update the roadmap's checklist in the same PR — and if
   you're writing user-facing docs (this site), match the pattern of every
   other page here: say plainly when something isn't built rather than
   staying quiet about it.

## Code style

- Python 3.11+, fully type-hinted.
- `ruff check` and `mypy` must pass; CI enforces this.
- Prefer explicit, readable code over metaprogramming.

## Tests

```bash
pytest
```

New framework-level behavior gets a test in `tests/`, following the existing
files' pattern of testing against real objects (a real `Container()`, a real
`fastapi.testclient.TestClient`) rather than mocks. Changes to the project
generator (`src/pyforge/console/stubs/`) should be validated by actually
running `pyforge new` against a temp directory and confirming the result
imports, serves, and — as of `0.7.0` — actually builds via
`python -m build` (see `tests/test_generator.py` for why that last check
exists: it's the regression test for a real bug a manual Docker
verification pass found).

## Working on this documentation site

This site lives in `docs-site/` (MkDocs + Material), separate from
`docs/architecture/` (internal design documentation for contributors —
see [08-documentation-architecture.md](https://github.com/pyforge-framework/pyforge/blob/main/docs/architecture/08-documentation-architecture.md)
for why the two are split). Every code sample on this site should reflect
something real — backed by a test in `tests/` or the generated project
template — never an aspirational example.

```bash
cd docs-site
pip install mkdocs mkdocs-material
mkdocs serve
```

## Commit messages / PRs

- Keep PRs focused; unrelated cleanup belongs in its own PR.
- Explain *why*, not just *what*, in the PR description.

## Reporting bugs / requesting features

Use [GitHub Issues](https://github.com/pyforge-framework/pyforge/issues).
For security vulnerabilities, see [SECURITY.md](https://github.com/pyforge-framework/pyforge/blob/main/SECURITY.md)
instead of opening a public issue.

## Code of Conduct

This project follows the [Contributor Covenant](https://github.com/pyforge-framework/pyforge/blob/main/CODE_OF_CONDUCT.md).
