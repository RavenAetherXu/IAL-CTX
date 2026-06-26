# Windows Deployment Runbook

This runbook covers the repo-prep Windows spoke package. It does not install
services, edit FRP, change firewall rules, or store credentials in this
repository.

## Scope

Tonight-ready:

- M0 local validation with an isolated `CTX_BASE`.
- Local `ctx-codex` self-test when Codex CLI is installed.
- Local spoke drill with `ctx-win-agent once` and a stub or local Codex bridge.

Requires operator-side VPS or hub setup:

- M1 FRP or SSH reachability to a hub ledger.
- Hub allowlists, ports, tokens, and FRP config.
- Any Windows service, scheduled task, firewall, or OpenSSH server changes.

## Prerequisites

- Windows 10 or later.
- Python 3.10 or later.
- Git for Windows or another clone mechanism.
- Optional: local Codex CLI for real `ctx-codex` execution.
- Optional for M1: Windows OpenSSH client and an operator-provided FRP client
  configuration kept outside this repository.

## M0 Local Validation

Use PowerShell from a fresh clone:

```powershell
cd packages\ctx-cli
$env:CTX_BASE = "$PWD\..\..\tmp\ctx-windows-m0"
python bin\ctx-route --help
```

Run the POSIX CI from Git Bash, WSL, or another bash-capable environment:

```bash
bash packages/ctx-cli/run-ci.sh
```

Run the built-in route drill with an isolated base:

```powershell
$env:CTX_BASE = "$PWD\..\..\tmp\ctx-windows-drill"
python bin\ctx-route drill
```

Register the Windows executor profile:

```powershell
$env:CTX_BASE = "$PWD\..\..\tmp\ctx-windows-agent"
python bin\ctx-win-agent register
python bin\ctx-route agent-list
```

Create a local route that requires Windows and Codex capability:

```powershell
python bin\ctx-route create `
  --route-id route_windows_local_codex `
  --target-site windows-local `
  --target-agent local-codex `
  --title-original "Windows local Codex smoke" `
  --capability os.windows,runtime.codex `
  --constraint read_only_first,no_secrets
```

For a real Codex self-test, use the default bridge:

```powershell
$env:CTX_CODEX = "python bin\ctx-codex-bridge"
python bin\ctx-win-agent once
python bin\ctx-route show route_windows_local_codex
```

For a no-Codex local lifecycle drill, use the bundled neutral stub executor:

```powershell
python bin\ctx-stub-agent demo --route-id route_windows_stub_demo
python bin\ctx-route show route_windows_stub_demo
```

The stub proves register -> claim -> execute -> reply without requiring Codex,
Kimi, or any other external AI CLI. It is intentionally not a semantic task
worker.

## M1 Spoke Framework

M1 connects the Windows spoke to a hub ledger. The hub remains the authority;
Windows can publish routes to the hub, claim eligible routes targeted at
Windows, and reply with metadata-first results.

Operator red-line steps, performed outside this repository:

- Configure hub-side FRP endpoint, allowlist, token, and ports.
- Provide Windows-side FRP client configuration without committing it.
- Provide SSH identity and access policy without copying keys or config into
  this repository.
- Confirm hub ledger path and `ctx-route` command on the hub.

Once the operator has configured the hub side, set only neutral command
environment on Windows:

```powershell
$env:CTX_REMOTE = "ctx-ledger@example.invalid"
$env:CTX_ROUTE = "<hub-side ctx-route command>"
$env:CTX_TRANSPORT = "frp-reverse-ssh:127.0.0.1:<hub-local-port>"
$env:CTX_DEVICE_ID = "windows-local"
python bin\ctx-win-agent register
python bin\ctx-win-agent once
```

`example.invalid` is a placeholder. Replace it only in the operator's local
environment or secret-managed deployment config, not in git. `CTX_TRANSPORT`
is audit metadata for profiles and replies; set it to the hub-local reverse
endpoint that the operator has already approved.

Publish a Windows-origin route to another hub device:

```powershell
python bin\ctx-win-agent publish `
  --target-site lingxiaodian `
  --target-agent codex `
  --title-original "Windows asks VPS for CTX status" `
  --capability os.linux,runtime.codex `
  --constraint read_only_first,no_secrets `
  --instructions "Inspect CTX status and reply with metadata-first evidence."
```

Run `python bin\ctx-win-agent once` when Windows should claim routes targeted
at `windows-local`.

## M1.5 Codex Runtime Injection

Routes that require `runtime.codex` are handled through `CTX_CODEX`. The
default is the bundled `ctx-codex-bridge`:

```powershell
$env:CTX_CODEX = "python bin\ctx-codex-bridge"
python bin\ctx-win-agent once
```

The bridge invokes local `codex exec`. Override the Codex command when needed:

```powershell
$env:CODEX_CMD = "codex"
python bin\ctx-codex-bridge run --task "Return a CTX verdict block" --timeout 600
```

Every successful Codex bridge run writes a metadata-first record under
`CTX_BASE\done\<task_id>.json` with kind `ctx-codex-result`. It does not read
Codex state databases, session files, `.env`, SSH config, or FRP config.
