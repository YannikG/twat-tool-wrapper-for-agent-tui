---
status: draft
entity: platform
sources: []
---

# Theme

## Purpose

Give TWAT an original, polished, compact desktop look in both dark and light
modes, so Qt defaults are never shown and the selected project/session is
visually unmistakable.

## Idea

An original dark-first visual direction: compact controls, a strong sidebar,
terminal-focused right panel, clear selected-state. Theme tokens live in JSON
(`dark.json`, `light.json`) and are rendered into a single app-wide QSS
template applied via the Fusion style. Only the tokens and QSS the current
slice needs are added.

## Must

- The app MUST apply a custom QSS in both dark and light modes.
- Theme tokens MUST be defined in JSON and rendered into QSS (no hardcoded
  colors in widget code).
- The Fusion style MUST be used as the base.
- Selected project/session MUST be visually unmistakable.
- Switching theme MUST restyle the whole app immediately.

## Must not

- Do not show unstyled Qt defaults.
- Do not add a webview for an "Electron look".
- Do not build a full design system upfront; add only what the current slice
  needs.
- Do not copy any reference app's styling.

## Acceptance criteria

- Dark and light themes each apply a coherent QSS to buttons, list rows, tabs,
  splitters, inputs, scrollbars, and status chips.
- The selected sidebar row is clearly distinct from unselected rows.
- Theme tokens are JSON; widget code references no literal colors.

## Verification

- Manual: toggle dark/light, confirm styling across the shell.
- `pytest-qt`: theme tokens render to a non-empty QSS; applying a theme does
  not raise.

## Related docs

- [`./settings.md`](./settings.md)
- [`./architecture-guardrails.md`](./architecture-guardrails.md)
