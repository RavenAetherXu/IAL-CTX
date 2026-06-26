# Windows M1 Acceptance Plan

Status: source checklist for the public alpha.

CTX's Windows M1 target is bidirectional task-layer collaboration through a hub
ledger:

```text
Windows can publish routes to the hub.
The hub can publish routes to Windows.
Both sides claim, execute, reply, and leave human-readable evidence.
```

FRP is transport, not authority. A Windows reverse SSH proxy lets the hub reach
Windows through a hub-local endpoint. Windows reaching the hub still uses an
operator-approved hub login or a future hub API.

## Current Gap

Public alpha now has the core pieces:

- Windows-safe record filenames.
- `ctx-win-agent register`, `publish`, `claim`, `execute`, `reply`, and `once`.
- `CTX_TRANSPORT` for operator-provided transport audit metadata.
- `ctx-stub-agent demo` for a no-Codex lifecycle proof.
- Cross-platform GitHub Actions matrix for Linux, macOS, and Windows.

The remaining gap is acceptance evidence across a real Windows spoke and hub.

## Acceptance Checklist

1. **M0 local lifecycle**
   - Run `python bin\ctx-route drill`.
   - Run `python bin\ctx-stub-agent demo --route-id route_windows_stub_demo`.
   - Confirm `python bin\ctx-route show route_windows_stub_demo` reports
     `status="replied"` and evidence kind `ctx-stub-result`.

2. **M1 registration**
   - Configure operator-provided `CTX_REMOTE`.
   - Configure hub-side `CTX_ROUTE`.
   - Configure `CTX_TRANSPORT` to the approved hub-local reverse endpoint.
   - Run `python bin\ctx-win-agent register`.
   - Confirm the hub shows device `windows-local` and agent
     `windows-local:codex-local` with accurate transport metadata.

3. **Windows -> hub publish**
   - Run `python bin\ctx-win-agent publish ... --target-site <hub-site>`.
   - Confirm the hub route has `origin_site="windows-local"` and
     `origin_agent="windows-local:codex-local"`.
   - Confirm the hub executor replies with metadata-first evidence.

4. **Hub -> Windows claim/reply**
   - Create a hub route targeting `windows-local` with capabilities
     `os.windows,runtime.codex` or `os.windows,probe.read-only`.
   - Run `python bin\ctx-win-agent once`.
   - Confirm the route reaches `status="replied"` and has a Windows executor
     identity in `reply.executed_by`.

5. **Audit and trace**
   - Run `ctx-route trace <route_id>` for both directions.
   - Confirm trace events show origin, target, claim, start, reply, and evidence.
   - Confirm no secret values are present in route instructions, replies, or
     artifacts.

## Production Follow-Ups

- Add a scripted M1 harness that runs the checklist end to end.
- Add a service/loop recipe for Windows after manual M1 passes repeatedly.
- Add a Kimi or other third-party adapter using `ctx-stub-agent` as the minimal
  implementation reference.
- Add a hub API or operator wrapper so users do not need raw SSH command strings
  for normal spoke registration and publishing.
