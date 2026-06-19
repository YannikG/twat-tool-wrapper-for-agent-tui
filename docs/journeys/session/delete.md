---
status: draft
entity: session
sources: []
---

# Delete sessions and projects — user journey

## User story

As a developer, I want to permanently remove finished sessions and unwanted
projects from TWAT so my sidebar stays clean, knowing my on-disk folders and
pi conversations are never deleted.

## Preconditions

- TWAT is launched with at least one project.

## Numbered user steps

### Delete an archived session

1. Expand **Archive** in the sidebar and **right-click** the session.
2. Choose **Delete** from the context menu.
3. A confirmation dialog appears: "Delete session '<name>'? This removes it
   from TWAT. The pi conversation file on disk is kept."
4. Confirm.
5. The session disappears from the sidebar and the Archive.

### Delete a project

1. **Right-click** a project in the sidebar.
2. Choose **Delete Project** from the context menu (the same menu has
   **Add Session**).
3. A confirmation dialog appears: "Delete project '<name>' and all its
   sessions? Running sessions are stopped first. The folder and pi
   conversations are NOT deleted."
4. Confirm.
5. Any running sessions in the project Stop gracefully; the project and all its
   sessions disappear from the sidebar.
6. The on-disk folder is untouched; it can be re-added later via Add Project.

## Expected result

Finished sessions and unwanted projects are gone from TWAT; the filesystem and
pi conversations are intact; the sidebar stays focused on active work.

## Link to spec

[`../../specs/session/delete.md`](../../specs/session/delete.md)
