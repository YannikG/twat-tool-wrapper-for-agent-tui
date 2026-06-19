---
status: draft
entity: platform
sources: []
---

# Settings (v1)

## Purpose

Define the only two user-facing settings for v1 and how they are edited, so the
settings surface stays minimal.

## Idea

v1 has exactly two settings: the UI theme (dark or light) and the `pi`
executable path. Both persist in the state file. The `pi` path is
autodiscovered from PATH and common install locations and prefilled; it can be
overridden only via the OS-native file picker. The theme is a toggle.

## Must

- The app MUST support a dark and a light theme.
- The `pi` path MUST be autodiscovered from PATH and common install locations
  (`/opt/homebrew/bin`, `/usr/local/bin`, `~/.local/bin`, and Windows
  `%APPDATA%\npm`, `%LOCALAPPDATA%` npm/pnpm dirs).
- The `pi` path field MUST be prefilled from autodiscovery.
- The `pi` path MUST be overridable via the native file picker only.
- Both settings MUST persist across restart.

## Must not

- No other settings in v1.
- No free-text `pi` path field.
- No settings import/export, sync, or profiles.

## Acceptance criteria

- On first launch, the `pi` path is prefilled if `pi` is found, else empty.
- Toggling theme switches dark/light styling app-wide immediately.
- Changing the `pi` path via the picker persists and is used as the launch
  target in later slices.
- Restart preserves both settings.

## Verification

- `pytest`: `pi` autodiscovery finds a planted executable; settings round-trip
  through the state file.
- Manual: toggle theme, change `pi` path, restart, confirm both persisted.

## Related docs

- [`./persistence.md`](./persistence.md)
- [`./theme.md`](./theme.md)
- [`../../../CONTEXT.md`](../../../CONTEXT.md)
