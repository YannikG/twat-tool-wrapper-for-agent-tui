# TWAT — Tool Wrapper for Agent TUIs

A local-first desktop shell around terminal sessions that run [`pi`](https://github.com/earendil-works/pi-coding-agent),
making the active project and session unmistakable so prompts stop going to the
wrong window.

Local-first. No accounts, cloud sync, telemetry, teams, or remote backends.

## Status

**v1 (macOS)** — usable via `uv run twat`. In-window terminal, project/session
tree, Start/Stop/Terminate, lifecycle hook, archive/restore/delete, themes,
instance lock, `/twat status` in pi.

**Windows** — PTY via ConPTY (`pywinpty`); PyInstaller builds in CI (see below).

Domain language: [`CONTEXT.md`](./CONTEXT.md). Manual test steps: [`docs/journeys/`](./docs/journeys/).

## Run (development)

Requires Python 3.12–3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run twat
```

## Develop

```bash
uv sync
uv run pytest                 # QT_QPA_PLATFORM=offscreen in CI
uv run ruff check
uv run mypy
```

Headless Qt: `QT_QPA_PLATFORM=offscreen uv run pytest`.

Quality gates: [`docs/specs/platform/quality-gates.md`](./docs/specs/platform/quality-gates.md).

## Build (PyInstaller)

Requires dev deps (`uv sync --group dev`). Produces a platform-native app bundle
under `dist/` (macOS `.app`, Windows `.exe`).

```bash
uv run python scripts/build/pyinstaller/build.py
```

Release builds run on tag push via [`.github/workflows/release.yml`](./.github/workflows/release.yml)
(four artifacts: macOS, Linux x64, Windows x64, Windows ARM64).
