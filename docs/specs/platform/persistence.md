---
status: draft
entity: platform
sources: []
---

# Persistence (state file)

## Purpose

Persist TWAT's local state so projects, session metadata, and settings survive
restart, without a database or any remote backend.

## Idea

A single JSON file in the platform config directory
(`~/.config/twat/state.json` on Linux,
`~/Library/Application Support/twat/state.json` on macOS,
`%APPDATA%/twat/state.json` on Windows). Written atomically (write to a temp
file, then rename). Stdlib `json` only.

## Must

- State MUST be a single JSON file in the platform config directory.
- Writes MUST be atomic (temp file + rename).
- The file MUST hold projects, session metadata, and settings.
- A missing or corrupt file MUST be treated as empty state, not a crash.

## Must not

- No database (SQLite or otherwise).
- No cloud sync, accounts, or remote storage.
- No secrets stored in the state file.

## Acceptance criteria

- Saving and reloading state round-trips projects and settings.
- A corrupt JSON file is recovered to empty state on load.
- The file is written via temp + rename (no partial writes visible).

## Verification

- `pytest`: round-trip projects + settings through the store on a tmp path;
  corrupt-file recovery; atomic write leaves no temp behind on success.

## Related docs

- [`./settings.md`](./settings.md)
- [`../../project/add-project.md`](../project/add-project.md)
- [`../../../CONTEXT.md`](../../../CONTEXT.md)
