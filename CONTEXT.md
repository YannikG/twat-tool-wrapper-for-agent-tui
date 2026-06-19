# TWAT

A local-first desktop shell around terminal sessions that run `pi`, making the
active project and session unmistakable so prompts stop going to the wrong
window.

## Language

**Project**:
A filesystem folder the user runs `pi` sessions in. Default name is the folder basename; user can override the display name.
_Avoid_: repo, workspace

**Session (TWAT session)**:
A TWAT-owned runtime handle: one running `pi` process bound to a Project, plus TWAT metadata (id, state, archive flag). It wraps at most one pi Session file; it is not the file itself.
_Avoid_: terminal, tab, conversation

**pi Session**:
pi's own persisted conversation (the `.jsonl` file pi owns and manages). A TWAT session references at most one pi Session file; TWAT never owns or copies the file.
_Avoid_: conversation file, session log (when the TWAT Session is meant)

**Binding**:
The association between a TWAT session and a pi Session file. Created at Start by whether the session was unbound (fresh `pi`) or bound (`pi --resume`); the authoritative file path always comes back from pi via the lifecycle hook, because pi is the file's owner. A running TWAT session may be temporarily unbound (no file path yet, or pi refused/got `--no-session`); that is a real state, not an error.
_Avoid_: link, reference, pointer

**New session (action)**:
Create a TWAT session record in the project: state `exited`, unbound, default name. Appears in the active sidebar. Does NOT launch `pi`; the user Starts it explicitly. (VM analogy: create the VM, power on later.)
_Avoid_: create session, start session

**Start (action)**:
Launch `pi`: `pi` if the session is unbound (fresh), `pi --resume <bound pi Session file>` if bound. Sets state to `running`; the binding is recorded from pi's `session_start` event.
_Avoid_: run, launch

**Stop (action)**:
Gracefully stop a running session: SIGTERM (POSIX) or a control-channel `ctx.shutdown()` (Windows). pi runs its `session_shutdown` hook and exits cleanly; state becomes `exited`.
_Avoid_: close, kill

**Terminate (action)**:
Hard-kill a running session: SIGKILL (POSIX) / TerminateProcess (Windows). Escape hatch when Stop hangs; state becomes `failed`. Separate button from Stop.
_Avoid_: force stop, kill

**Archive (action)**:
Hide a session from the active sidebar and show it under the archive. If the session is running, gracefully Stop it first, then set the archived flag. If already stopped, just set the flag. The pi Session conversation is untouched.
_Avoid_: delete, close

**Restore (action)**:
Un-set the archived flag on a stopped session so it reappears in the active sidebar, still `exited`. Does NOT launch `pi`; the user Starts to resume the conversation.
_Avoid_: reopen, resume (use Start)

**State file**:
TWAT's single JSON persistence file in the platform config directory (`~/.config/twat/`, `~/Library/Application Support/twat/`, `%APPDATA%/twat/`). Holds projects, session metadata, and settings. Written atomically (tmp + rename). Stdlib `json`, no database.
_Avoid_: database, store, config file (when the state file is meant)

**Hook endpoint**:
A localhost-only HTTP listener TWAT runs to receive lifecycle events from the twat-hook extension inside each pi session. Auto-allocated ephemeral port, per-session random token. The port and token are injected into each pi child via `TWAT_HOOK_PORT` / `TWAT_HOOK_TOKEN`; another local process cannot forge events without the token. See ADR-0002.
_Avoid_: webhook, callback, server

**twat-hook (extension)**:
The generated TypeScript extension TWAT writes to `.pi/extensions/twat-hook.ts` in a project so pi can emit lifecycle events back to TWAT. Single canonical filename with a `// @twat-version <version>` header. It reads port/token/session id from the process env at runtime (not baked in). On Start, if the file is missing or its header version differs from the running TWAT's version, TWAT rewrites it with the current version's content; the on-disk hook always matches the TWAT that last started a session. TWAT never edits `.gitignore`; the user is told to ignore the file if they wish.
_Avoid_: plugin, callback script

**Connection status**:
Whether a running session's twat-hook has a reachable live hook endpoint and has ACK'd a recent event. Surfaced in the sidebar as an indicator and via the `/twat status` command inside the pi terminal.
_Avoid_: connected, online

**Repair session (action)**:
Force-regenerate `twat-hook.ts` at the current TWAT version, gracefully Stop the session, then Start it again. Escape hatch for a stale or broken hook. Right-click menu entry.
_Avoid_: fix, reset

**Instance lock**:
A single app-wide lock file (in the platform state dir) that allows only one TWAT instance to run per machine. Held for the app's lifetime; checked via PID + liveness on startup. A second launch refuses (or focuses the existing instance). No per-session locks: if only one TWAT runs, no two instances can resume the same pi Session file. Single-instance is per-machine, not per-network-home.
_Avoid_: session lock, file lock

**Launcher**:
The command TWAT runs inside a session's PTY. A login shell (`$SHELL`, falling back to `/bin/bash`; Git Bash on Windows, PowerShell only if pi works there) sources the user's rc so `pi` is on PATH and env is native, then runs `pi`; on pi exit it drops to an interactive shell so output is visible and the user can re-launch. Hook env (`TWAT_*`) is inherited by pi as a child of the shell.
_Avoid_: runner, executor

**pi exit detection**:
How TWAT learns a session's `pi` has exited to flip state to `exited`/`failed`. Primary signal: the `session_shutdown` hook event. Fallback: PTY child-process death (crash, force-kill, or broken hook) flips to `failed`/`exited`.

**Session state**:
The life of the TWAT session's `pi` process handle: `starting`, `running`, `exited` (ended cleanly), `failed` (crashed or killed unexpectedly). Independent of what pi's agent is doing internally.
_Avoid_: status, completed (use exited)

**Agent activity**:
What pi's agent loop is doing: `idle` (waiting for a prompt) or `working` (a turn is running). Ephemeral, comes from pi lifecycle events; shown as a secondary indicator, not as the session state.
_Avoid_: session state, busy

**Archived**:
A boolean flag on a TWAT session, orthogonal to session state. An archived session is hidden from the active list and shown in the archive; it can be Restored (un-flagged) and then Started to resume the conversation. Almost always also `exited`.
_Avoid_: closed, done, completed

**Terminal panel**:
The in-window embedded surface (right panel) where a selected TWAT session's `pi` runs and the user types. There is no external-terminal mode; embedding is a hard requirement (see ADR-0001).
_Avoid_: terminal window, external terminal

**Rename (action)**:
Set a TWAT session's name from inside the pi terminal. Names are never typed in TWAT. The twat-hook extension tries to intercept pi's native `/name` via the `input` event for instant emission; if that does not fire for built-in commands, `/twat-rename` is the canonical instant path (it calls `pi.setSessionName()` and emits the name to TWAT immediately). Regardless of path, `session_start` and `turn_end` re-emit the current name as an eventually-consistent backstop, so a native `/name` done out-of-band is never silently stale forever.
_Avoid_: rename session (use Rename), title
