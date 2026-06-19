---
status: draft
entity: session
sources: []
---

# Archive and restore a session — user journey

## User story

As a developer, I want to set aside finished sessions without deleting the
conversation, so my active sidebar stays focused on work in progress, and bring
an archived session back when I want to resume it.

## Preconditions

- TWAT is launched.
- A project is added with at least one session.

## Numbered user steps

1. Select a session in the sidebar that you are done with.
2. Click **Archive** (or right-click → Archive).
3. If the session is running, pi Stops gracefully; the session then disappears
   from the active list and appears under **Archive**.
4. If the session is already stopped, it moves to Archive immediately.
5. The conversation file is untouched — the history is preserved.
6. Later, expand **Archive**, select the session, click **Restore**.
7. The session reappears in the active list, state `exited`. pi is not running.
8. Click **▶ Start** to resume the conversation (`pi --session <bound file>`).

## Expected result

Finished sessions are hidden but preserved; the active sidebar stays clean; a
restored session resumes its conversation on Start.

## Link to spec

[`../../specs/session/archive.md`](../../specs/session/archive.md)
