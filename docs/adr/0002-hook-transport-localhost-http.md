# 0002 — Lifecycle hook transport is a localhost HTTP endpoint

TWAT receives pi lifecycle events by running a localhost-only HTTP listener
that the twat-hook extension POSTs to from inside each running pi session.

We rejected Unix-domain-socket / named-pipe IPC because the hook is TypeScript
running in pi via `fetch()`, and HTTP to 127.0.0.1 is the obvious cross-platform
path; a UDS/pipe would add Windows-specific complexity for no benefit. We
rejected an ASGI framework (uvicorn + starlette) as unjustified for a single
token-gated localhost endpoint; stdlib `http.server` in a background thread
suffices.

The port is auto-allocated (bind 0, ephemeral) and the per-session token is
random; both are injected into each pi child via `TWAT_HOOK_PORT` and
`TWAT_HOOK_TOKEN`. This avoids fixed-port collisions and means only pi
processes TWAT itself spawns can authenticate. The trust boundary is: a local
process that can read a pi child's env could impersonate it — acceptable for a
local-first desktop tool, documented as a known boundary.

The listener lives for the app's lifetime; events are handed to the Qt main
thread. This choice is hard to reverse once the generated extension script
depends on it.
