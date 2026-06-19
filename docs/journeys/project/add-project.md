---
status: draft
entity: project
sources: []
---

# Add project — user journey

## User story

As a developer with many project folders, I want to add a folder as a Project
so that, later, I can run `pi` sessions in it with the project context
unmistakably visible in the sidebar and terminal header.

## Preconditions

- TWAT is launched.

## Numbered user steps

1. Click **Add Project** in the sidebar.
2. The OS-native folder picker opens.
3. Pick a project folder and confirm.
4. A name prompt appears, prefilled with the folder basename.
5. Optionally edit the name, then confirm.
6. The project appears in the sidebar.
7. Click the project in the sidebar.
8. The right panel shows the terminal placeholder with the project name and
   working directory; the OS window title also shows the project name.
9. Quit and relaunch TWAT.
10. The project is still in the sidebar.

## Expected result

The project is added, selectable, and persists across restart. No real
terminal or `pi` runs in this slice.

## Link to spec

[`../../specs/project/add-project.md`](../../specs/project/add-project.md)
