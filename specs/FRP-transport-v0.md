# SPEC: FRP Transport v0

Basis timestamp: 2026-06-12T07:20:00Z

FRP v0 is a constrained transport adapter for cross-device reachability.

Current 2026-06-14 runtime rule:

- FRP is the primary live cross-device transport.
- Preferred Huaguoshan CTX routes use Lingxiaodian-local ledger operations and
  FRP reverse SSH `127.0.0.1:6022` only for fixed Huaguoshan read-only probes.
- Do not assume WireGuard, `10.8.*`, or inner-network fallback.
- Huaguoshan-outbound public SSH `<LEDGER_HOST>:22` ledger polling is legacy
  compatibility and implementation debt. It is not a stable CTX control-plane
  design primitive, especially after Huaguoshan observed `:22` timeouts while
  FRP `<LEDGER_HOST>:7000` stayed reachable.

Required properties:

- server-side TLS/token authentication
- port allowlist
- control port rate limiting
- guard for failed token or non-TLS attempts
- local-only sensitive proxy ports
- status command that prints metadata only

Forbidden properties:

- public exposure of Mac SSH proxy
- raw token printing
- raw config dumping
- private key transfer by default
- using transport connectivity as task authorization
