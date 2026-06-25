# Contributing

By contributing you agree to the Contributor License Agreement in
[`CLA.md`](./CLA.md), which lets the project relicense and offer the combined
work (including the future Apache-2.0 grant and commercial editions).

Keep CTX neutral: core routing and audit code must not privilege a specific
executor engine. Executors register capabilities and audit profiles through the
same `ctx-agent-profile-v1` contract.

Before submitting changes, run:

```sh
bash packages/ctx-cli/run-ci.sh
```

Also check for accidental secret-shaped content:

```sh
rg -n "sk-|Bearer [A-Za-z0-9]|BEGIN .*PRIVATE|auth\\.token|client_secret|password\\s*=|token\\s*=" .
```

Do not commit runtime ledgers, scopes, handoff files, stdout logs, `.env`
files, private keys, FRP config, SSH private config, real IP inventories, or
personal host paths.
