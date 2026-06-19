---
status: draft
entity: platform
sources: []
---

# Definition of Done

## Purpose

A living checklist of what "done" means for TWAT v1. Grows as slices ship, but
every new item stays inside the product guardrails (local-first, desktop-only,
no accounts/cloud/sync/telemetry/teams/subscriptions/remote backends).

## Idea

The initial DoD is the human-testable v1 outcome. Each slice advances a subset
of these items. An item is checked only when its slice is verified by a human.

## Initial DoD

- [ ] App launches locally.
- [ ] User can add a project from a folder.
- [ ] A real terminal runs in-window for the selected project (login shell in
      the project folder; colors and TUI apps render).
- [ ] User can create a new `pi` session for a project.
- [ ] User can start/stop/terminate sessions (VM-style controls).
- [ ] User can resume an existing known session for a project via Start.
- [ ] Multiple sessions can stay open and be switched without losing state.
- [ ] Session Rename changes from `pi` update the desktop UI.
- [ ] Real pi lifecycle events drive binding, agent activity, and exit.
- [ ] User can archive and restore sessions.
- [ ] Dark/light mode works.
- [ ] `pi` path is autodiscovered, prefilled, and can be overridden with a
      native file picker.
- [ ] Custom Qt styling is applied in both themes.
- [ ] The pi extension script is generated at `.pi/extensions/twat-hook.ts`.
- [ ] The smallest relevant automated checks pass.
- [ ] A human can manually test the slice with documented steps.

## Must (every new DoD item)

- Help manage project-bound `pi` / agent TUI sessions.
- Be local-first and desktop-only.
- Be documented in specs and journeys before implementation.

## Must not (a new item is rejected if it)

- Adds accounts, cloud sync, telemetry, teams, subscriptions, or remote
  backends.

## Acceptance criteria

v1 is done when every initial DoD item above is checked and verified by a
human.

## Verification

Each item maps to a slice's manual test steps (see `docs/journeys/`) and the
automated checks in [quality-gates](./quality-gates.md).

## Related docs

- [`./quality-gates.md`](./quality-gates.md)
- [`./architecture-guardrails.md`](./architecture-guardrails.md)
- [`../../../CONTEXT.md`](../../../CONTEXT.md)
