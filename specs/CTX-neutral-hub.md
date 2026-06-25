# SPEC: CTX Neutral Hub (agent-agnostic coordination)

Status: **draft (v0-draft), for human + cross-agent review. Do not implement
unilaterally.**
Basis: 2026-06-15 · Author: Lingxiaodian pi/Fable

## 0. Intent

CTX must be a **neutral coordination hub** — a public agent infrastructure — not
a codex tool nor a pi tool. Any agent (codex, pi/Fable, claude-code, gemini-cli,
a future runtime) must be able to:

- **self-register** a capability profile,
- be **discovered and routed to by capability**, never by a hard-coded name,
- **change** its engine/version/id and keep collaborating (stable identity, not
  brittle string literals),
- and join an existing collaboration without any engine code change.

The CTX one-liner is unchanged; this spec only neutralizes *who* executes:

```
FRP connects. CTX coordinates. Secret Box authorizes. Local agents execute. Humans audit.
                       ▲ neutral                              ▲ pluggable
```

## 1. Current coupling (what this spec removes)

Evidence from the live tree (2026-06-15):

| # | Coupling | Location | Fix |
|---|---|---|---|
| C1 | doctor has per-name audit special-casing | `ctx-route` ~L1346-1372: `if executed_by == "lingxiaodian:codex"` / `"huaguoshan-macos:codex"` | make audit rules **data-driven** from the agent profile |
| C2 | claimant hard-codes a target whitelist | `ctx-lingxiao-agent` L52: `ALLOWED_TARGET_AGENTS = {"codex","ctx-codex","local-native"}` | match by **capability**, not name set |
| C3 | no executor abstraction; capabilities unused for routing | global; `required_capabilities` recorded but never matched | **executor adapter contract** + capability matchmaking |

Already-neutral (keep as-is): the ledger data model accepts any `agent_id` /
`device_id` / `target_agent` as free-form strings with no whitelist; any agent
can already register and claim. This spec builds on that, it does not replace it.

## 2. Agent identity: stable key, mutable id

Problem: `AGENT_ID` is a module constant (e.g. `lingxiaodian:codex`). If an
agent changes engine/version, the literal id breaks links and audit rules.

Resolution — two-level identity:

- `agent_key` — **stable, opaque, lifetime identity** of an agent slot on a
  device. Example: `lingxiaodian/primary-reasoner`. Never changes when the
  underlying engine changes.
- `agent_id` — **current binding**, derived/registered, may change:
  `<device>:<engine>` e.g. `lingxiaodian:fable`, later `lingxiaodian:codex`.
- `instance_id` — existing per-process lease identity (unchanged).

Routing, leases, and audit bind to `agent_key` + `capabilities`. `agent_id` is
display/provenance only. When an agent changes, it re-registers the same
`agent_key` with a new `agent_id`/`capabilities`; in-flight routes follow the key,
new routes follow capability. This is the "auto-update id, keep collaborating"
requirement.

## 3. Agent profile (self-describing registration)

Each agent publishes a non-secret profile via `ctx-route agent-register`
(generalizes today's `device-upsert` + `agent-heartbeat`). Stored append-only;
latest wins per `agent_key`.

```json
{
  "schema": "ctx-agent-profile-v1",
  "agent_key": "huaguoshan/local-pi",
  "agent_id": "huaguoshan-macos:pi",
  "device_id": "huaguoshan-macos",
  "engine": { "name": "pi", "version": "0.78.1", "model": "claude-opus-4.8" },
  "kind": "executor",
  "capabilities": ["macos", "pi", "read-only-probe", "gui"],
  "constraints_supported": ["read_only_first", "no_secrets"],
  "transports": ["frp-reverse-ssh:127.0.0.1:6022", "home-file-drop"],
  "availability": "intermittent",
  "audit_profile": {
    "result_link_kind": "ctx-pi-reply-v1",
    "expects_thread_id": false,
    "ephemeral_session": true
  },
  "registered_at": "ISO8601Z",
  "red_lines": ["metadata_first", "no_secret_values"]
}
```

`audit_profile` is the key to removing C1: **doctor reads each agent's declared
audit expectations instead of hard-coding `== "lingxiaodian:codex"`.** Codex's
existing checks become one profile (`result_link_kind: ctx-codex-result`,
`expects_thread_id: true`); pi's become another; new agents declare their own or
inherit a default.

## 4. Executor adapter contract

The "standard coupling" any agent implements to be a CTX executor. It is a thin
behavioral contract over the existing route lifecycle — not a new daemon.

```
register()  -> publish ctx-agent-profile-v1 (kind=executor) + capabilities
claim(route)-> only if route.required_capabilities ⊆ self.capabilities
               and route.constraints ⊆ self.constraints_supported
               (atomic claim + lease on the ledger; never double-claim)
execute(route) -> run locally in the agent's own permission context
reply(route)-> metadata-first ctx reply: status, summary, evidence, artifacts,
               secret_events, residual_risk, next_action
```

Adapters are interchangeable. Today's pieces become the first three registered
adapters, with **no behavior change**:

| adapter | engine | replaces hard-coding |
|---|---|---|
| `ctx-codex` | codex exec | L1 bridge, already exists |
| `ctx-pi-worker` / `ctx-lx-worker` | pi `-p` | AGENT_ID const → profile |
| `ctx-huaguoshan-frp-agent` | fixed probes | a minimal read-only adapter |

A new agent ships ONE adapter that implements the four verbs + a profile; it
needs zero engine changes to join.

## 5. Capability-driven matchmaking (removes C2/C3)

Routes already carry `required_capabilities`. New rule, enforced where claims are
gated (claimant and/or a generic matchmaker), replacing name whitelists:

```
eligible(route, agent) :=
    route.target_site   == agent.device_id
 && route.status        == "queued"
 && route.required_capabilities ⊆ agent.capabilities
 && route.constraints           ⊆ agent.constraints_supported
 && not route.approval_required          (unless agent is approval-capable)
 && route.secret_capabilities == []      (until Secret Box exists)
```

`target_agent` becomes optional/advisory: a route may target a *capability set*
(`required_capabilities`) rather than a named agent. Named targeting still works
(back-compat) but is no longer required. Engine stops needing any agent-name
literal.

## 6. Engine neutralization tasks (C1)

In `ctx-route`:
- Replace `executed_by == "lingxiaodian:codex"` / `"huaguoshan-macos:codex"`
  blocks with: look up `agent_key`'s `audit_profile`, apply generic checks
  (`result_link_kind` present? `expects_thread_id` honored? `ephemeral_session`
  suppresses the warn?).
- Move the codex/pi seed/demo agents out of engine literals into registered
  profiles / test fixtures.
- Net: `grep -c codex ctx-route` should trend toward 0 in non-test code.

## 7. Migration (incremental, non-breaking)

1. Add `agent-register` + `ctx-agent-profile-v1` storage (additive; keep
   `device-upsert`/`agent-heartbeat` as compatibility shims).
2. Register codex, pi(LX), pi(HGS), frp-probe as profiles → behavior identical.
3. Switch doctor to read `audit_profile` (delete C1 literals).
4. Switch claimants to capability `eligible()` (delete C2 whitelist).
5. Add a generic capability matchmaker; `target_agent` becomes advisory.
6. Prove a NEW agent (e.g. a throwaway `echo-agent`) joins by registering a
   profile only — zero engine edits — as the neutrality acceptance test.

Each step keeps the working forward/reverse pi and codex paths green.

## 8. Relationship to the Go production build

This contract is exactly what must be **frozen before the Go rewrite**:

```
Python: define + stabilize {agent profile, executor adapter, capability routing}
        -> validate with codex + pi + one new agent
        -> FREEZE the neutral-hub interface
Go:     compile the neutral engine (ctx-route) against the frozen contract
```

Do not Go-compile while the executor interface still embeds codex/pi names.

## 9. Non-goals

- Not adding agent *authorization* (that is Secret Box, a separate project).
- Not a new daemon or message bus; stay file-backed JSON + leases.
- Not removing named targeting; making it optional.
- Not changing the FRP-first transport boundary or the single-source-of-truth
  ledger principle.

## 10. Acceptance criteria

- `ctx-route` contains no agent-name literal in non-test code paths.
- A new agent collaborates after `agent-register` only, no engine change.
- An agent that changes engine (new `agent_id`, same `agent_key`) keeps its
  routes and audit continuity.
- Existing codex + pi forward/reverse routes remain verified and green.

## Review questions for the next round

1. Two-level identity (`agent_key` stable + `agent_id` mutable) — agreed?
2. `audit_profile` in the agent profile as the mechanism to delete doctor's
   hard-coded codex checks — agreed?
3. `target_agent` demoted to advisory, routing primarily by
   `required_capabilities` — agreed?
4. Freeze-before-Go ordering — agreed?

---

# 11. Cross-audit resolution (v0.1)

Huaguoshan pi (executor-side) reviewed v0-draft over CTX route
`route_20260615T034902Z_pi_neutralhub_review` (verified accepted). Verdict:
**approve all 4 directions, nothing blocks neutralization**, gated on two
pre-freeze items + documented residuals. Resolution below.

## 11.1 Grounding correction (engine atomicity already exists)

Huaguoshan reviewed without the engine in its tree and assumed the central ledger
has "no compare-and-swap." That is **incorrect** — `ctx-route` already implements
the atomic claim primitive it asked for:

- Claim runs under `with locked():` = `fcntl.flock(LOCK_EX)` (ctx-route L165/585),
  then **compare-and-set**: `if route.status != "queued": raise not claimable`
  (L587-588), then `atomic_write` (L478). Read-then-write racing is already
  forbidden at the ledger.
- Lease TTL exists: `--lease-seconds` → `lease.expires_at` (L593-600),
  `lease_expired()` (L338-341); reclaim via `requeue` (L713).

So freeze-gate (a) is **mostly already satisfied**. The spec adopts and hardens it:

- **Atomic-claim primitive (normative):** all claims MUST go through the single
  always-on Lingxiaodian ledger under its `flock(LOCK_EX)` + status-CAS +
  `atomic_write`. "read status then write claim" without the lock is forbidden.
- **Single-writer rule:** the ledger is single-host by design (FRP-first / A2:
  remote agents never write the ledger directly). `flock` is only sound on a
  local FS, so the ledger MUST NOT be placed on a shared/network mount. Cross-host
  claiming is always proxied to the one Lingxiaodian ledger. This is already our
  topology; the spec now states it as a hard invariant.
- **Auto-reclaim (new):** a generic reaper MUST `requeue` routes whose lease is
  `lease_expired()` (TTL default 1200s, per-route overridable), returning them to
  `queued` so capability routing does not strand routes on intermittent/crashed
  executors. This closes Huaguoshan risk #2.

## 11.2 audit_profile hardening (freeze-gate b — accepted in full)

audit_profile as drafted was self-attestation and `ephemeral_session` could
silence the auditor. Adopted changes:

- **Claim-time pinning:** doctor evaluates the audit_profile **version in effect
  at route-claim time**, snapshotted onto the route, NOT the latest profile. An
  agent cannot flip flags after a failing route to retroactively pass.
- **Checked, not trusted:** doctor verifies the *observed reply shape* matches the
  declared `result_link_kind`, rather than accepting the agent's word.
- **Strict default + no self-suppression:** unknown/missing audit_profile defaults
  to the **strict** profile (warn-on-missing, loud). `ephemeral_session` may only
  *relabel* a missing-session finding to INFO, it may NOT suppress reply-shape or
  evidence checks.

## 11.3 Capability semantics locked before freeze (Q3)

- **Controlled vocabulary:** capabilities are tokens from a registered namespace
  (`specs/CTX-capability-vocab.md`, to be added), not free strings. Unknown tokens
  in `required_capabilities` → route is unroutable (loud), not silently eligible.
- **Version predicates:** capability tokens MAY carry a version constraint
  (`pi>=0.78`). Flat-token-only is rejected as too coarse. Exact grammar frozen in
  the vocab spec.
- **Truthfulness:** declared capabilities are unverified until Secret Box; doctor
  SHOULD add capability probes where cheap (e.g. transport reachability). Over-
  declaration is tracked as Secret-Box-era debt.
- **Tie-break / fan-out:** when N agents are `eligible()`, policy is
  **first-atomic-claim-wins** (the flock/CAS above is the arbiter). Stated
  explicitly; no scoring in v0.

## 11.4 agent_key ownership (Q1 gap — documented as Secret-Box debt)

Identity-takeover surface (any process could `agent-register` an arbitrary
`agent_key`) is real and created by the "key survives engine change" property.
v0 rule, enforcement deferred to Secret Box:

- **First-writer-pins-key:** the first registration of an `agent_key` records its
  `device_id` + transport origin. Later rebinds MUST originate from the same
  `device_id`/transport, else rejected (or flagged until Secret Box enforces).
- `agent_id = <device>:<engine>` is not unique; when multiple instances share an
  `agent_key`, `instance_id` disambiguates leases and first-claim-wins routing.

## 11.5 Other residuals (documented, not blocking)

- Constraint enforcement stays executor-trusted (`constraints ⊆
  constraints_supported` is a claim, not enforcement) until Secret Box. Noted.
- `secret_capabilities == []` is a **hard, default-deny** precondition in
  `eligible()`: a missing field reads as "unknown → deny", never as "no secrets".

## 11.6 Freeze checklist (must all be frozen before Go)

1. `ctx-agent-profile-v1` schema
2. executor adapter verbs `register/claim/execute/reply`
3. **capability vocabulary + version-predicate grammar** (Huaguoshan addition)
4. `eligible()` predicate (incl. default-deny secret gate)
5. **audit_profile evaluation rule** (claim-time-pinned, checked, strict default)
6. atomic-claim/lease/auto-reclaim primitive + single-writer invariant

Items 3 and 5 are flagged as the most likely to still be "soft" when someone
declares frozen — explicit gate.

## 11.7 Status

Design consensus reached (Lingxiaodian + Huaguoshan). No blocking issues.
Implementation proceeds incrementally on the existing Python engine; freeze (and
only then Go) after the §11.6 checklist is met and validated against codex + pi +
one new throwaway agent.
