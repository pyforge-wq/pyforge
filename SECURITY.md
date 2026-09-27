# Security Policy

## Supported Versions

PyForge is pre-`1.0`. Only the latest published `0.x` release is supported
with security fixes until `1.0.0`, after which a proper support matrix will
be documented here.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report privately via
[GitHub Security Advisories](https://github.com/pyforge-wq/pyforge/security/advisories/new)
for this repository. Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal PyForge app that demonstrates the issue, if
  applicable)
- Any known mitigations

You should receive an acknowledgement within a few business days. We'll work
with you to understand and address the issue before any public disclosure,
and credit reporters in the fix's release notes unless you prefer otherwise.

## Scope

This policy covers the `pyforge-framework` package in this repository.
Vulnerabilities in dependencies (FastAPI, Starlette, Pydantic, etc.) should
be reported to those projects directly; if a PyForge-specific workaround or
version pin is warranted in the meantime, report it here as well.
