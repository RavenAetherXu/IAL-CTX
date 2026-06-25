# SPEC: CTX L0 Ledger

Basis timestamp: 2026-06-12T07:20:00Z

L0 is the append-only event and result ledger.

Required records:

- task created
- scope created
- route created
- route claimed
- action started
- artifact produced
- result replied
- verification completed
- blocked or needs approval

Storage v0:

```text
runtime/scopes/*.jsonl
runtime/done/*.json
runtime/shared/state.json
```

Production runtime currently lives outside this repository at
`<CTX_BASE>`.
