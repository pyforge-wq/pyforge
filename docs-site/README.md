# PyForge documentation site

The end-user documentation site — task-oriented guides for people *building
with* PyForge. Built with [MkDocs](https://www.mkdocs.org/) +
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

This is separate from [`docs/architecture/`](../docs/architecture/), which
is internal design documentation for framework contributors — see
[08-documentation-architecture.md](../docs/architecture/08-documentation-architecture.md)
for why the two are split.

## Run it locally

```bash
pip install -r requirements.txt
mkdocs serve
```

Visit `http://127.0.0.1:8000/`. Pages rebuild live as you edit.

## Build

```bash
mkdocs build --strict
```

`--strict` fails the build on broken internal links or navigation entries —
CI runs this on every push, so a stale link fails the same way a broken
test would.

## Content rule

Every code sample here should be real — backed by a test in `tests/` or the
generated project template — never aspirational. Where a feature isn't
built yet, say so directly (see any page's "What's not built" section for
the pattern) rather than staying quiet about it.
