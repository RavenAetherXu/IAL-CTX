# ASC Context Engine

ASC Context Engine is the external nervous system for ASC multi-agent and
multi-device collaboration.

It coordinates agents, devices, tasks, evidence, routes, secret-backed
capabilities, and human audit surfaces without turning the transport layer into
an unrestricted remote-control channel.

## Project name and status

This repository is **CTX (Context Engine)** — the **prototype and alpha**
implementation (Python) of **Noether**, the action-trust layer of Information
Ascension Lab. CTX is where the design is proven in practice; the **Noether**
name is **reserved for the future Go rewrite** that will carry the hardened,
production form (see the project's repo/Go strategy ADR).

In short: **CTX = Noether's prototype / alpha.** Treat this repository as
alpha-stage: the architecture and contracts are real and tested, but interfaces
may still change before the Noether (Go) release.

## License

Licensed under the **Functional Source License, Version 1.1, Apache 2.0 Future
License (FSL-1.1-ALv2)** — see [`LICENSE`](./LICENSE) and a plain-language
summary in [`LICENSING.md`](./LICENSING.md).

- Free for internal use, non-commercial education and research, and
  non-competing use.
- **Competing commercial use requires a separate license** — see
  [`COMMERCIAL-LICENSE.md`](./COMMERCIAL-LICENSE.md).
- Each version converts to Apache-2.0 two years after its release.
- Contributions are under [`CLA.md`](./CLA.md); names/logos under
  [`TRADEMARK.md`](./TRADEMARK.md).

## Final Design Sentence

```text
FRP connects.
CTX coordinates.
Secret Box authorizes.
Local agents execute.
Humans audit.
```

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the repository
hierarchy, per-module control logic, platform support, and roadmap.

## Quickstart

CTX is a file-backed coordination ledger with a single-file Python CLI. No
build step, no server, no database.

### Prerequisites

- Python 3.10+ (CI runs on 3.12; only the standard library is used).
- Optional: a local execution engine (e.g. the Codex CLI) if you want an
  executor to actually run claimed routes. CTX core never bundles one.

### Install

```sh
git clone <this-repo-url> ctx
cd ctx

# CTX stores all state under CTX_BASE. Pick any directory you own.
export CTX_BASE="$HOME/.ctx-data"
export CTX_SITE="my-laptop"          # how this node labels routes it creates
export CTX_ACTOR="alice"             # who you are, for provenance

# Put the CLI on PATH (or call it by full path).
export PATH="$PWD/packages/ctx-cli/bin:$PATH"

ctx-route --help
```

That is the whole installation: clone, set `CTX_BASE`, run `ctx-route`. State
is created lazily on first use.

### 60-second tour (verified end-to-end)

```sh
# 1. Register an executor agent (any engine; here a Codex executor).
cat > codex.json <<'JSON'
{
  "schema": "ctx-agent-profile-v1",
  "agent_key": "my-laptop/codex",
  "agent_id": "my-laptop:codex",
  "device_id": "my-laptop",
  "engine": {"name": "codex", "version": "external", "model": "operator-selected"},
  "kind": "executor",
  "capabilities": ["os.linux", "runtime.codex", "ctx.route"],
  "constraints_supported": ["read_only_first", "no_secrets"],
  "transports": ["transport.local"],
  "audit_profile": {"result_link_kind": "ctx-codex-result", "expects_thread_id": true},
  "secret_capabilities": [],
  "red_lines": ["metadata_first", "no_secret_values"]
}
JSON
ctx-route agent-register --profile-file codex.json
ctx-route agent-list

# 2. Create a route that needs the runtime.codex capability.
ctx-route create \
  --target-site my-laptop \
  --capability runtime.codex --capability os.linux \
  --title-original "hello ctx" \
  --instructions "echo hello"

# 3. See the unified route board and check who can claim it by capability.
ctx-route routes
ctx-route agent-match <route_id>

# 4. An executor adapter then claims -> executes -> replies; you verify.
#    (see "Executor adapters" below for the four-verb contract)
ctx-route doctor          # health, diagnostics
```

Run the test suite at any time:

```sh
bash packages/ctx-cli/run-ci.sh
```

## Connecting a real engine (e.g. Codex)

CTX core only coordinates and records. To make routes actually execute, you run
an **executor adapter** next to your engine.

A neutral, cross-platform reference Codex bridge is now **included** as
`packages/ctx-cli/bin/ctx-codex-bridge`: it runs your local `codex exec`, redacts
secret-shaped output, and writes a `ctx-codex-result` — it never reads Codex
state, sessions, or any secret. Claimant adapters invoke it through the
`CTX_CODEX` environment variable, so you can also swap in your own bridge.
Reference claimants: `ctx-win-agent` (Windows/portable), `ctx-lingxiao-agent`
(Linux). Other engines implement the same four-verb contract — see below.

## Run on Windows

CTX runs on Windows (the route ledger lock is cross-platform). If you have Codex
on Windows, you can clone, validate, and execute routes locally, then optionally
join a hub as a spoke. See [`docs/WINDOWS-DEPLOYMENT.md`](./docs/WINDOWS-DEPLOYMENT.md)
for the step-by-step runbook (`ctx-win-agent` + `ctx-codex`).

## Runtime Boundaries

CTX keeps all live state under `CTX_BASE` and out of git. Never commit:

| Area | Path | Git policy |
|---|---|---|
| CTX runtime state | `<CTX_BASE>` | task records, routes, scopes, logs — do not commit |
| Transport configs | e.g. `/etc/frp` | live transport config / allowlists — never import |
| Secrets | tokens, keys, `.env`, SSH config | never commit, never print |

## Module Map

```text
specs/
  CTX-L0-ledger.md            append-only ledger model
  CTX-L1-local-bridge.md      local single-device coordination
  CTX-L2-cross-device-routing.md   cross-device routing
  CTX-L3-chamber.md           multi-agent deliberation (spec)
  FRP-transport-v0.md         transport boundary
  Secret-Box-v0.md            capability/secret authorization (design)

packages/
  ctx-cli/          the CTX CLI (bin/) + tests + run-ci.sh
  route-ledger/     future append-only ledger helpers (placeholder)
  secret-box/       future boxed action broker (placeholder)

runtime/
  README.md         why runtime state is not committed
```

`huaguoshan` and `lingxiaodian` are example device codenames retained for
historical route compatibility and tests. They are not privileged roles in CTX;
new devices and executors register through the same profile and capability
mechanism.

## Executor adapters

CTX core is a neutral coordination, routing, and recording layer. It must not
embed, require, or privilege any execution engine. `ctx-codex` and `codex-cli`
are external executor adapters supplied by an operator and injected through
`CTX_CODEX`; other engines use the same registration and routing contract.

The executor contract has four verbs:

1. `register`: publish a `ctx-agent-profile-v1` with identity, kind,
   capabilities, transport, constraints, and audit profile.
2. `claim`: claim an eligible route by device, agent, and optional instance.
3. `execute`: run the local engine under the route's constraints without
   exposing secret values.
4. `reply`: write structured evidence, artifacts, residual risk, and next
   action back to the route ledger.

Example external Codex adapter profile:

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

## Status

CTX is an early but working file-backed engine:

- **Working:** route lifecycle (`create/claim/start/reply/verify`), neutral
  capability-based routing and self-registration (`agent-register/agent-match`),
  trace chains, route doctor/dashboard diagnostics, lifecycle recovery
  (`expire/cancel/requeue`), a circuit breaker, lease/instance accounting, an
  isolated reliability drill (`ctx-route drill`), and stability batches.
- **Design-stage:** Secret Box authorization, L3 deliberation chamber, and the
  planned Go rewrite under the Noether product name.
- **Known limit:** cross-device transport latency (over FRP reverse tunnels) is
  the main blocker to claiming 24/7 durable autonomy; single-node local use is
  fast and stable.

Cross-device transport configuration (FRP, etc.) is operator-specific and lives
outside this repository.

## Design Principles

1. Transport is not authority.
2. Agents use capabilities, not raw secrets.
3. Cross-device freedom happens at the task layer, not by unrestricted shell.
4. Local agents should execute local work.
5. Humans must be able to inspect route, status, evidence, and artifacts.
6. Every secret-backed action must be metadata-audited and value-redacted.
7. Start file-backed and lightweight; add daemons only after repeated need.
8. The control plane coordinates; home/edge devices are local capability and
   execution planes.
9. CTX transparency is a safety invariant: every cross-device action must be
   human-readable, traceable, and tied to evidence.
```
