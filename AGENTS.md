# ASC Context Engine Agent Rules

## Purpose

This repository is the versioned engineering home for ASC Context Engine,
Secret Box, route ledgers, and transport governance specs.

It is not the live runtime directory.

## Hard Boundaries

- Do not store token, API key, private key, password, `.env`, FRP config, SSH
  private config, shell history, or credential values in this repository.
- Do not copy files from `/etc/frp`, `<HOME>/.ssh`, `<CODEX_HOME>`,
  private model/tool configs, or any secret-bearing path into this
  repository.
- Do not import `<CTX_BASE>/done`, `scopes`, `shared/state.json`,
  route records, stdout logs, or handoff files into git.
- Do not mutate systemd, firewall, sshd, fail2ban, FRP, launchd, Docker, cron,
  or live service configs while editing this repository unless the user
  explicitly asks for an operational change.
- Treat `<CTX_BASE>` as runtime state. Read it only when necessary and
  avoid reading files likely to contain secrets.

## Edit Scope

Safe default edit areas:

- `README.md`
- `docs/`
- `specs/`
- `packages/*/README.md`
- future source code under `packages/`, after local design exists

Do not add implementation code that reads secrets until Secret Box policy,
redaction, and audit tests exist.

## Verification

Before finalizing changes, run at least:

```text
git status --short
rg -n "sk-|Bearer [A-Za-z0-9]|BEGIN .*PRIVATE|auth\\.token|client_secret|password\\s*=|token\\s*=" .
```

If source code is added later, add project-specific tests and document them in
the final response.
