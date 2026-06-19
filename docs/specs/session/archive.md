---
status: draft
entity: session
sources: []
---

# Archive and restore a session

## Purpose

Let the user tidy the active sidebar by archiving finished sessions without
losing the conversation, and bring them back when needed. Archive is orthogonal
to session state: it is just a flag that hides a session from the active list
and shows it under the archive.

## Idea

A Session carries an `archived` boolean (default `false`). Archiving a running
session gracefully Stops it first (SIGTERM, as in lifecycle), then sets the
flag; archiving a stopped session just sets the flag. The pi Session
conversation file is never touched. Restoring un-sets the flag on a stopped
session; it reappears in the active sidebar, still `exited`, and the user
Starts to resume. Archive/Restore never launch pi.

```mermaid
stateDiagram-v2
    [*] --> active: New session
    active --> active: Start/Stop/Terminate
    active --> archived: Archive (Stop first if running)
    archived --> active: Restore
    note right of archived: still exited; pi never auto-launched
```

## Must

- A Session MUST have an `archived` boolean; default `false`.
- Archive MUST set the flag; if the session is `running`/`starting`, it MUST
  Stop (graceful) first and wait for the process to end before flagging.
- Restore MUST un-set the flag on a stopped session; it MUST NOT launch pi.
- The archived flag MUST persist across restart.
- The sidebar MUST hide archived sessions from the active list and show them
  under an Archive section.
- Archiving MUST NOT touch the pi Session conversation file (TWAT never owns it).

## Must not

- Do not delete sessions on Archive (the conversation survives).
- Do not launch pi on Restore (Start is explicit).
- Do not allow Restore of a session that is still `running` (Restore targets
  stopped sessions; a running archived session is a contradiction — Archive
  Stops first).
- Do not tie archive to session state (they are orthogonal booleans/states).

## Acceptance criteria

- A stopped session can be Archived; it disappears from the active list and
  appears under Archive.
- A running session can be Archived; pi is Stopped gracefully, then the session
  moves to Archive.
- An archived session can be Restored; it reappears in the active list, state
  `exited`; pi is not running.
- Restart preserves the archived flag.
- The pi Session conversation file is unchanged by Archive/Restore.

## Verification

- `pytest`: Session model `archived` flag + persistence; AppService
  archive/restore (with a fake process adapter so no real pi in CI).
- Manual: see [journey](../../journeys/session/archive.md).

## Related docs

- [`./lifecycle.md`](./lifecycle.md)
- [`../../../CONTEXT.md`](../../../CONTEXT.md) (Archive, Restore, Archived)
