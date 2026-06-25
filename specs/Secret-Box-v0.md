> MIGRATED: canonical Secret Box now lives in <SECRET_BOX_REPO>. This copy is frozen history.

# SPEC: Secret Box v0

Basis timestamp: 2026-06-12T07:20:00Z

Secret Box v0 is a local, metadata-first action broker.

## Records

Registry entries contain:

- secret ID
- label
- capability
- risk level
- backend reference
- allowed actions
- disallowed actions
- approved callers
- approval policy

Registry entries do not contain:

- secret values
- value hashes
- prefixes or suffixes
- private key bodies

## Commands

```text
secret-box list
secret-box describe <secret_id>
secret-box run <secret_id> <allowed_action>
secret-box audit
secret-box doctor
```

## Acceptance

- unknown actions are refused
- unknown callers are refused
- all outputs are redacted
- every action emits an audit event
- audit records are metadata-only
