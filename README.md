# TWAT — Tool Wrapper for Agent TUIs

A local-first desktop shell around terminal sessions that run [`pi`](https://github.com/earendil-works/pi-coding-agent),
making the active project and session unmistakable so prompts stop going to the
wrong window.

Local-first. No accounts, cloud sync, telemetry, teams, or remote backends.

## Status

Pre-alpha. Scaffolding only — see [`CONTEXT.md`](./CONTEXT.md) for the domain
language and [`docs/specs/platform/definition-of-done.md`](./docs/specs/platform/definition-of-done.md)
for what "done" means.

## Develop

Requires Python 3.12–3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                       # set up the environment
uv run pytest                 # tests
uv run ruff check             # lint
uv run mypy                   # types
```

Headless Qt: `QT_QPA_PLATFORM=offscreen uv run pytest`.

See [`docs/specs/platform/quality-gates.md`](./docs/specs/platform/quality-gates.md)
for the full gate list.
