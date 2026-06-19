---
status: draft
entity: session
sources: []
---

# Start and stop a pi session — user journey

## User story

As a developer, I want to create a `pi` session for a project, start it on
demand, and stop it cleanly, so I control exactly when pi runs and can keep
several sessions open and switch between them.

## Preconditions

- TWAT is launched.
- A project is added and selected.
- The `pi` path is set (Settings) and `pi` runs in that folder.

## Numbered user steps

1. Select a project in the sidebar.
2. Click **+ New Session** in the toolbar above the terminal area.
3. A session tab appears (state `exited`, default name).
4. Click **▶ Start** in the toolbar.
5. `pi` launches in the project folder; the terminal panel shows pi's TUI.
6. The session tab shows state `running`.
7. Create a second session and Start it; switch back to the first tab — its
   terminal is still showing pi, running.
8. Click **⏹ Stop** with the first session's tab active.
9. pi exits gracefully; the session tab shows `exited`.
10. Click **▶ Start** again — pi resumes (fresh, since no binding yet).
11. (If Stop hangs) click **✕ Terminate** — pi is hard-killed; state `failed`.
12. Quit and relaunch TWAT — session tabs persist, all `exited`.

## Expected result

VM-style control of pi sessions: create without launching, Start/Stop/Terminate
explicitly, multiple sessions alive and switchable, metadata persisted.

## Link to spec

[`../../specs/session/lifecycle.md`](../../specs/session/lifecycle.md)
