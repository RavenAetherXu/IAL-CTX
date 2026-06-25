# Security Policy

Report suspected vulnerabilities privately to the repository owner or project
maintainer before opening public issues.

Do not include token values, API keys, private keys, passwords, `.env` content,
FRP config, SSH private config, shell history, route ledgers, stdout logs, or
runtime state in reports or patches.

This repository is for specs, docs, and source. Live runtime state belongs
outside git under `<CTX_BASE>`, and secret-bearing systems remain outside this
repository.
