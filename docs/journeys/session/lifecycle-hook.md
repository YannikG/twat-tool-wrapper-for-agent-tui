---
status: draft
entity: session
sources: []
---

# Lifecycle hook live — user journey

## User story

As a developer, I want TWAT to know my session's pi name, working state, and
exit automatically, so I never rename or track it by hand and the sidebar is
always accurate.

## Preconditions

- TWAT is launched, a project is added, a session is created and selected.
- The `pi` path is set.

## Numbered user steps

1. Click **▶ Start** on the session.
2. `.pi/extensions/twat-hook.ts` is generated in the project (with a version
   header); TWAT's localhost listener receives a `session_start` event.
3. The sidebar shows the session's binding/name reported by pi.
4. Send a prompt to pi; the sidebar shows agent activity `working`.
5. When the agent finishes a turn, activity returns to `idle`.
6. Inside pi, run `/twat-rename Refactor auth` (or `/name Refactor auth`).
7. The sidebar session name updates to `Refactor auth` automatically.
8. Quit pi (`/exit` or Ctrl+D).
9. TWAT marks the session `exited` (no manual sync).

## Expected result

Real pi lifecycle events drive binding, name, agent activity, and exit — no
manual tracking, no faking.

## Link to spec

[`../../specs/session/lifecycle-hook.md`](../../specs/session/lifecycle-hook.md)
