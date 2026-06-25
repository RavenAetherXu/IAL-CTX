# SPEC: CTX Capability Vocabulary v0 (freeze item #3)

Status: **draft for freeze.** Basis: 2026-06-15. Co-authored: Lingxiaodian pi/Fable
(matchmaker seat) + Huaguoshan pi (executor seat, route
`route_20260615T035521Z_pi_profile_ratify`).

Referenced by `specs/CTX-neutral-hub.md` §11.3 / §11.6 item 3.

## 1. Design decisions (frozen)

- **Namespaced, flat, enumerable tokens** of the form `<facet>.<token>`.
  Matching is **presence-only set membership**: `required ⊆ agent.capabilities`.
- **Capability = WHAT, not WHICH.** Version/precision is NOT encoded in tokens.
  A route needing pi ≥ 0.78 declares capability `runtime.pi` AND a structural
  predicate on `engine.version` (`>= 0.78`), evaluated by the matchmaker at
  routing time. This keeps the token set finite and freezable (Huaguoshan call,
  accepted).
- **Controlled vocab:** tokens outside this registry make a route **unroutable
  (loud)**, never silently eligible (spec §11.3).
- **Reserve-don't-claim:** a token may exist in the vocab but be claimed by no
  current agent (e.g. `ui.gui`).

## 2. v0 token set

| Facet | Token | Meaning |
|---|---|---|
| os | `os.linux` | host OS Linux |
| os | `os.macos` | host OS macOS |
| os | `os.windows` | host OS Windows (reserved) |
| runtime | `runtime.pi` | executes under pi |
| runtime | `runtime.codex` | executes under codex |
| runtime | `runtime.shell` | fixed shell/probe runtime |
| exec | `exec.shell` | can run shell/bash |
| fs | `fs.read` | filesystem read |
| fs | `fs.write` | filesystem write (capability; gated by route constraints) |
| probe | `probe.read-only` | read-only inspection mode |
| net | `net.frp` | operates over the FRP tunnel |
| transport | `transport.file-drop` | home file-drop mailbox transport |
| transport | `transport.local` | same-host local ledger access |
| ctx | `ctx.route` | can drive the ctx-route ledger |
| ctx | `ctx.smoke` | L2 smoke/liveness checks |
| reason | `reason.general` | general reasoning/synthesis executor |
| ui | `ui.gui` | drive a desktop GUI (**reserved, unclaimed**) |

## 3. Structural predicate grammar (version/engine)

A route MAY carry `required_engine` alongside `required_capabilities`:

```json
"required_capabilities": ["runtime.pi", "os.macos"],
"required_engine": { "name": "pi", "version_min": "0.78.0" }
```

Matchmaker rule (extends `eligible()`):
```
required_capabilities ⊆ agent.capabilities
AND (required_engine absent OR
     (agent.engine.name == required_engine.name
      AND semver(agent.engine.version) >= semver(required_engine.version_min)))
```
`required_engine` is optional; absence means "any engine that has the caps".

## 4. Canonical capabilities of the first 4 agents

| agent_key | capabilities (v0 vocab) |
|---|---|
| lingxiaodian/codex-bridge | `os.linux runtime.codex exec.shell ctx.route` |
| lingxiaodian/primary-reasoner | `os.linux runtime.pi ctx.route reason.general` |
| huaguoshan/local-pi | `os.macos runtime.pi exec.shell fs.read probe.read-only net.frp transport.file-drop` |
| huaguoshan/frp-probe | `os.macos runtime.shell probe.read-only net.frp ctx.smoke` |

(huaguoshan/local-pi reflects Huaguoshan's ratified correction: `ui.gui` dropped,
`exec.shell`+`fs.read` added.)

## 5. Open for next round

- `fs.write` vs constraint interaction (capability present but route
  `read_only_first` must still win) — enforcement is Secret-Box-era.
- Per-token owner/probe (capability truthfulness) — Secret-Box debt (spec §11.3).
- Whether `reason.*` needs sub-tokens (code, audit, plan) — defer until a route
  actually needs to discriminate.
