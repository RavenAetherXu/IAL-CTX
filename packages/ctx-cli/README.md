# ctx-cli

Source-of-truth home for lightweight CTX CLI helpers.

> New here? Start with the **Quickstart** in the repository [`README.md`](../../README.md)
> (clone, set `CTX_BASE`, run `ctx-route`).


Current helpers:

- `bin/ctx-route` - file-backed L2 route lifecycle helper.
- `bin/ctx-codex-bridge` - neutral, cross-platform reference Codex bridge. Runs your
  local `codex exec`, redacts secret-shaped output, writes a `ctx-codex-result`;
  never reads Codex state, sessions, or secrets. Injected via `CTX_CODEX`.
- `bin/ctx-win-agent` - Windows/portable executor adapter
  (`register/claim/execute/reply/once`). See `docs/WINDOWS-DEPLOYMENT.md`.
- `bin/ctx-lingxiao-agent` - manual-first Lingxiaodian local agent that claims
  safe `target_site=lingxiaodian` routes and invokes the Codex bridge via
  `CTX_CODEX` (default `ctx-codex-bridge`).
- `bin/ctx-mac-agent` - manual-first Huaguoshan macOS local agent that claims
  safe `target_site=huaguoshan-macos` read-only probe routes.
- `bin/ctx-mac-codex-agent` - manual-first Huaguoshan macOS Codex agent that
  claims safe `target_site=huaguoshan-macos,target_agent=codex` routes and
  invokes Codex CLI in read-only ephemeral mode.

The macOS Codex claimant is manual-first by design. Do not install it as a
persistent launchd job until quota controls, session labeling, and route schema
validation exist.

By default it invokes Codex with `--ephemeral`. Set
`CTX_MAC_CODEX_PERSIST_SESSION=1` only for explicit white-box session-history
tests where retaining the Codex session is desired and safe.

Responsibilities:

- inspect routes
- inspect task state
- create route envelopes
- show link status
- show human-readable task traces
- show route doctor/dashboard health
- run explicit TCP transport probes in doctor/dashboard, for example
  `--transport-probe mac-ssh=127.0.0.1:6022`
- claim/start/reply/verify route records under explicit state transitions
- expire/cancel/requeue stuck or failed route records after origin-side review
- validate route/reply schema before writes
- assign and inherit `trace_id` across `reply_to` route chains
- render a human-readable or JSON trace using `ctx-route trace <route_id>`
- reject explicit child `trace_id` values that conflict with the parent route
- mark legacy or cross-trace reply links in trace output instead of silently
  merging unrelated chains
- expose only allowlisted L1 task JSON metadata in trace output, with
  secret-shaped text redacted and long summaries truncated
- expose route reply task references, including safe `ctx-codex` task IDs and
  Codex thread IDs when present
- tolerate recoverable claim/start races in claimant loops so duplicate agent
  instances do not crash the whole loop
- register and inspect executor profiles through `ctx-route agent-register`,
  `ctx-route agent-list`, and `ctx-route agent-show`

## Executor adapters

CTX core does not embed, require, or privilege any execution engine. Codex is
one external executor adapter among peers: `ctx-codex`/`codex-cli` must be
provided by the operator and injected through `CTX_CODEX`. Other executors
register profiles and claim work through the same route lifecycle.

Adapter contract:

1. `register`: publish a `ctx-agent-profile-v1` profile with `kind=executor`,
   capabilities, constraints, transports, and audit fields.
2. `claim`: claim an eligible route by device, agent, and optional instance.
3. `execute`: run local work under the route constraints without reading or
   printing secret values.
4. `reply`: write structured route evidence, artifacts, residual risk, and
   next action.

Example external Codex profile:

```json
{
  "schema": "ctx-agent-profile-v1",
  "agent_key": "example-device/codex",
  "agent_id": "example-device:codex",
  "device_id": "example-device",
  "engine": {"name": "codex", "version": "external", "model": "operator-selected"},
  "kind": "executor",
  "capabilities": ["os.linux", "runtime.codex", "ctx.route"],
  "constraints_supported": ["read_only_first", "no_secrets"],
  "transports": ["transport.local"],
  "audit_profile": {
    "result_link_kind": "ctx-codex-result",
    "expects_thread_id": true,
    "ephemeral_session": false,
    "thread_field": "codex_thread",
    "thread_id_field": "id",
    "thread_model_field": "model",
    "thread_id_output_field": "codex_thread_id",
    "thread_model_output_field": "codex_thread_model"
  },
  "secret_capabilities": [],
  "red_lines": ["metadata_first", "no_secret_values"]
}
```

No implementation should read or print secret values.

Runtime deployment currently targets:

```text
<CTX_BASE>/bin/
```

Runtime route records, device profiles, scopes, stdout logs, and state files
must not be copied back into this repository.
