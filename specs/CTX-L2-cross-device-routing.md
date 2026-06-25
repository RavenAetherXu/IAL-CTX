# SPEC: CTX L2 Cross-Device Routing

Basis timestamp: 2026-06-13T15:35:14Z

L2 routes tasks across devices and sites.

Lingxiaodian is the L2 control plane because it is the always-on site. It owns
the canonical route ledger, shared status, reply records, verification state,
and human audit surface.

Target devices are local capability planes. They claim routes, execute local
work under local authority, and publish structured replies.

Sites:

- Lingxiaodian VPS
- Huaguoshan macOS
- Huaguoshan Windows
- Huaguoshan Shuiliandong Linux VM

Naming rule:

```text
Shuiliandong (水帘洞) is the Huaguoshan built-in Linux VM.
Colima may be the current implementation substrate, but CTX route topology
should name the system role as Shuiliandong.
```

Rule:

```text
Move intent and evidence through CTX.
Do not move unrestricted shell authority through FRP.
```

Human transparency rule:

```text
No cross-device action is complete unless a human can inspect its route,
caller, target, constraints, evidence, artifacts, residual risk, and
verification state.
```

Route statuses:

- planned
- queued
- claimed
- running
- replied
- verified
- blocked
- needs_approval
- expired
- failed
- cancelled

Route storage v0:

```text
<CTX_BASE>/routes/planned/*.json
<CTX_BASE>/routes/queued/*.json
<CTX_BASE>/routes/running/*.json
<CTX_BASE>/routes/done/*.json
```

Device profile storage v0:

```text
<CTX_BASE>/devices/*.json
<CTX_BASE>/links/*.json
```

Minimum route object:

```json
{
  "route_id": "route_YYYYMMDDTHHMMSSZ_0000",
  "trace_id": "trace_or_root_route_id",
  "created_at": "2026-06-13T00:00:00Z",
  "created_by": "human|codex|fable|asc|local-agent",
  "origin_site": "lingxiaodian",
  "origin_agent": "codex",
  "target_site": "huaguoshan-macos",
  "target_agent": "codex|fable|asc|local-native",
  "task_kind": "inspect|implement|verify|operate|handoff|review",
  "title_original": "raw request or triggering event",
  "title_auto": "[macos-gui] concise task title",
  "required_capabilities": ["macos", "gui"],
  "constraints": ["read_only_first", "no_secrets"],
  "approval_required": true,
  "secret_capabilities": [],
  "status": "queued",
  "lease": null,
  "artifacts_expected": ["summary", "evidence"],
  "transparency": {
    "human_readable": true,
    "trace_required": true,
    "evidence_required": true,
    "secret_values_allowed": false
  }
}
```

Trace rules:

- New routes without `reply_to` default `trace_id` to their own `route_id`.
- New routes with `reply_to` inherit the parent route's `trace_id`.
- A child route must reject an explicit `trace_id` that conflicts with the
  parent route.
- Trace output may include legacy `reply_to` chains that predate `trace_id`,
  but it must label those inclusions and warn on cross-trace links instead of
  silently merging unrelated chains.

Minimum reply object:

```json
{
  "route_id": "route_YYYYMMDDTHHMMSSZ_0000",
  "status": "replied|blocked|needs_approval|failed",
  "executed_by": "huaguoshan-macos:codex",
  "summary": "human-readable result",
  "evidence": [],
  "artifacts": [],
  "secret_events": [],
  "residual_risk": "what was not verified",
  "next_action": "verify|approve|reroute|none"
}
```

Minimum human commands:

```text
ctx status
ctx routes
ctx route show <route_id>
ctx route trace <route_id>
ctx route doctor
ctx route dashboard
ctx route transcript <route_id>
ctx route artifacts <route_id>
ctx route evidence <route_id>
ctx links
ctx devices
```

Optional transport probe:

```text
ctx route doctor --transport-probe mac-ssh=127.0.0.1:6022
```

Transport probes are diagnostics only. They prove whether a named TCP endpoint
is reachable at check time; they do not grant authority and do not replace route
leases, device profiles, or origin-side verification.

Current transport truth from the 2026-06-14 Huaguoshan audit:

- FRP is primary for live cross-device routing.
- Lingxiaodian-to-Huaguoshan uses `mac-ssh=127.0.0.1:6022`.
- Huaguoshan-outbound route-ledger polling over public SSH
  `<LEDGER_HOST>:22` is legacy compatibility and implementation debt, not a
  stable CTX control-plane path.
- FRP-first Huaguoshan local-native routes should be claimed by a
  Lingxiaodian-side claimant such as `ctx-huaguoshan-frp-agent`. That claimant
  performs `claim/start/reply/verify` against the local Lingxiaodian ledger and
  uses `127.0.0.1:6022` only for the fixed Huaguoshan read-only action. This is
  the preferred replacement for Huaguoshan outbound public-SSH ledger polling.
- Public SSH `:22` and FRP `:7000` must be diagnosed separately because
  Huaguoshan observed `:22` timeouts while `:7000` stayed reachable.
- WireGuard, `10.8.*`, and inner-network fallback are out of scope unless a
  human explicitly re-enables them after fresh runtime validation.

Lifecycle recovery commands:

```text
ctx route expire <route_id> --reason ...
ctx route cancel <route_id> --reason ...
ctx route requeue <route_id> --reason ... [--force]
```

Recovery rules:

- Origin-side verification must close replied, failed, expired, or cancelled
  routes so the active queue remains readable.
- Active routes with unexpired leases must not be expired or requeued without
  explicit human review.
- Requeue clears the lease and increments `retry_count`.
- Duplicate/replay handling in v0 is diagnostic: duplicate route records,
  cross-trace links, and stale lifecycle state are surfaced by doctor output.
  Cryptographic replay protection is future Secret Box/Ledger work.

Red lines:

- Lingxiaodian must not become an unrestricted remote-control substrate.
- FRP/SSH/Matrix/mailbox connectivity is transport, not authorization.
- No secret values, private configs, token-bearing command lines, or credential
  material may enter route records or replies.
- Home-device sleep, disconnect, or loss of link should move routes to queued,
  expired, or blocked. It must not cause aggressive reconnect loops.
- A remote reply is not accepted until verified by the origin side or the human.
