# SPEC: CTX L1 Local Bridge

Basis timestamp: 2026-06-12T07:20:00Z

L1 bridges local heterogeneous CLI agents on one machine.

Current deployed example:

```text
Fable or ASC Pi -> ctx-codex -> Codex exec -> result record
```

Requirements:

- task ID
- scope ID
- title, brief, and title provenance
- caller and spawned-by fields
- target runtime
- constraints
- stdout/stderr captured separately
- result summary
- artifact diff metadata
- human status command

Non-goal:

- Do not route Codex-native internal workers through CTX.
