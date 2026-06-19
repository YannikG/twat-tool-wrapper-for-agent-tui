---
status: draft
entity: platform
sources: []
---

# Common language

## Purpose

One canonical place for TWAT's domain terms, so specs, journeys, code, and UI
agree on vocabulary.

## Idea

The glossary lives in [`../../../CONTEXT.md`](../../../CONTEXT.md). It is the single
source of truth. This file only points to it and records *where* a term's
decision was made, so a reader can trace why a word means what it does.

Architectural decisions that shaped the language are recorded as ADRs:

- [`../../adr/0001-in-window-terminal-embedding.md`](../../adr/0001-in-window-terminal-embedding.md)
  — why "Terminal panel" is in-window only.
- [`../../adr/0002-hook-transport-localhost-http.md`](../../adr/0002-hook-transport-localhost-http.md)
  — why the "Hook endpoint" is a localhost HTTP listener.

## Must

- Every domain term used in specs, journeys, or code MUST match a term in
  `CONTEXT.md`.
- When a new term is resolved, it is added to `CONTEXT.md` first, then used.

## Must not

- Do not duplicate term definitions in specs or journeys; link to
  `CONTEXT.md` instead.
- Do not invent synonyms for terms that already have an `_Avoid_` list.

## Verification

`scripts/ci/verify_docs.py` checks that `CONTEXT.md` exists and that internal
markdown links resolve.

## Related docs

- [`../../../CONTEXT.md`](../../../CONTEXT.md)
- [`./architecture-guardrails.md`](./architecture-guardrails.md)
- [`./quality-gates.md`](./quality-gates.md)
