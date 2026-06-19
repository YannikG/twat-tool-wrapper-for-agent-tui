---
status: draft
entity: platform
sources: []
---

# Open terminal in project — user journey

## User story

As a developer, I want to open a real terminal inside TWAT for a selected
project, so I can run shell commands in that project's folder without leaving
the window or risking a wrong-window prompt.

## Preconditions

- TWAT is launched.
- At least one project is added and selected.

## Numbered user steps

1. Select a project in the sidebar.
2. The right panel shows the project name and an **Open Terminal** button.
3. Click **Open Terminal**.
4. The user's login shell starts in the project folder, in-window.
5. Type `pwd` — it prints the project folder.
6. Type `echo $SHELL` — it prints the shell TWAT launched.
7. Run a color test, e.g. `printf '\033[31mred\033[0m\n'` — "red" renders in red.
8. (Optional) run a TUI such as `vim`/`htop` if installed — it uses the
   alternate screen.
9. Resize the window — the terminal resizes with it.
10. Select a different project — the current terminal stops; the new project's
    placeholder appears. (State is not preserved across switches yet.)
11. Close the window — the shell is terminated (no orphan process).

## Expected result

A working embedded terminal per selected project, rendering colors and TUI
apps, with clean lifecycle on switch/close. No `pi` runs in this slice.

## Link to spec

[`../../specs/platform/terminal-embedding.md`](../../specs/platform/terminal-embedding.md)
