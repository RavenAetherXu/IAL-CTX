# CTX Architecture & Module Map

This document describes the repository hierarchy and the control/processing
logic of each module, so a new operator can understand what runs where.

## 1. Repository hierarchy

```text
.
├── README.md            entry point + Quickstart
├── LICENSE / LICENSING / NOTICE / CLA / TRADEMARK / COMMERCIAL-LICENSE
├── SECURITY.md / CONTRIBUTING.md / AGENTS.md
├── docs/
│   └── ARCHITECTURE.md  (this file)
├── specs/               frozen design contracts (L0–L3, capability vocab, FRP)
├── packages/
│   ├── ctx-cli/
│   │   ├── bin/         the CLI engine + reference executor adapters
│   │   ├── tests/       stdlib unittest suite
│   │   └── run-ci.sh    local CI (tests + neutrality + drift gates)
│   ├── route-ledger/    placeholder for future ledger helpers
│   └── secret-box/      placeholder (Secret Box migrated to its own repo)
└── runtime/             placeholder; live state lives under CTX_BASE, not git
```

## 2. Layered model

- **L0 Ledger** — append-only, file-backed, single source of truth under
  `CTX_BASE`. Atomic writes + a global lock + leases.
- **L1 Local bridge** — single-device, multi-agent coordination.
- **L2 Cross-device routing** — route to other devices by capability.
- **L3 Chamber** — multi-agent deliberation (spec only).

Control flows down, evidence flows up. Every boundary conserves one invariant
(responsibility, evidence, permission, locality, human sovereignty).

## 3. Modules and their control logic

### Neutral core (engine)

| Module | Role | Control / processing logic |
|---|---|---|
| `bin/ctx-route` | **The engine.** Everything else is a client of it. | File-backed route lifecycle: `create → claim → start → reply → verify`, plus `expire/cancel/requeue` recovery. Holds the global lock (`_acquire_lock`, cross-platform: `fcntl` on POSIX, `msvcrt` on Windows). Self-registration (`agent-register/agent-list/agent-show`) and **capability-based matching** (`agent-match`): a route is eligible for an agent iff `route.required_capabilities ⊆ agent.capabilities` and `route.constraints ⊆ agent.constraints_supported`; `secret_capabilities` are default-deny. Data-driven audit via each agent's `audit_profile` (no engine is privileged). Adds `trace_id` chains, `doctor`/`dashboard` diagnostics, a circuit breaker, lease/instance accounting, `drill` (isolated reliability self-test), and `stability-create/report`. **No engine, no secret, no remote shell is embedded here.** |

### Reference executor adapters (examples; device/engine-specific)

These are sample claimants showing the four-verb contract
(`register/claim/execute/reply`). They are not privileged — any new engine
implements the same contract. Names use the project's historical device
codenames; treat them as templates.

| Module | Runs on | Control logic |
|---|---|---|
| `bin/ctx-lingxiao-agent` | a Linux control node | Claims eligible local routes, invokes an **external** Codex bridge named by `CTX_CODEX`, writes a metadata-first reply. |
| `bin/ctx-mac-codex-agent` | a macOS node with Codex | Claims `target_agent=codex` routes, runs Codex CLI in ephemeral read-only mode, replies. |
| `bin/ctx-mac-agent` | a macOS node | Polls the ledger over SSH, claims fixed read-only probe routes. Legacy outbound-SSH path. |
| `bin/ctx-huaguoshan-frp-agent` | the hub, reaching an edge node | Keeps ledger writes local on the hub, reaches the edge node only through an FRP reverse-SSH endpoint for fixed read-only probes. |
| `bin/ctx-lx-worker` / `bin/ctx-pi-worker` | control node / edge node | pi-based executors for reverse routes. |
| `bin/ctx-lx-reverse-poller` / `bin/ctx-huaguoshan-pi-bridge` | control node | Hub side of a pull-model reverse (edge→hub) transport; edge never dials the ledger outbound. |
| `bin/ctx-lease-reaper` | control node | Auto-reclaims routes stranded on crashed/intermittent executors (requeue/expire with a retry cap). |
| `bin/ctx-hgs` | edge node | Local, ledger-agnostic status dashboard for the edge device. |

## 4. End-to-end control flow

```text
origin            ctx-route (ledger)           executor adapter
  │  create ───────────▶ queued                      │
  │                      │  (agent-match by capability)
  │                      ◀──────────── claim ─────────│
  │                      │             start          │
  │                      │                         execute (local, constrained)
  │                      ◀──────────── reply ─────────│  (evidence/artifacts)
  │  verify ────────────▶ verified                    │
```

## 5. Platform support

- **Linux / macOS:** full support.
- **Windows:** `ctx-route` (the engine + CLI) is portable as of the
  cross-platform lock (`fcntl`→`msvcrt`). You can clone, set `CTX_BASE`, and
  run the full route/registry/doctor lifecycle locally. SSH-based adapters
  require the OpenSSH client (built into Windows 10+). To *execute* routes with
  Codex you still supply your own Codex bridge via `CTX_CODEX`.

## 6. Roadmap (not yet in this repository)

These are designed/intended but **not shipped here**; do not assume they exist:

- **A reference `ctx-codex` bridge** — a minimal, neutral adapter that wraps a
  local Codex CLI so routes execute out of the box. Today the bridge is
  operator-supplied.
- **FRP transport packaging** — only the boundary policy is in `specs/`. Live
  FRP server/client config, tunnels, and the reverse-SSH endpoint are
  operator-specific and live outside this repo.
- **Mesh / federation** — connecting multiple hubs (e.g. two independent VPS
  control planes) into one collaboration fabric for human↔agent and agent↔agent
  work across organizations. This is a core long-term goal but currently exists
  only as vision/design, with **no code or spec in this repository yet**.
- **Secret Box** — capability/secret authorization (L3 power-trust); migrated to
  its own repository.
- **Go rewrite under the Noether product name** — after interface freeze and
  MVP stability (see the project's ADR on repo/Go strategy).
