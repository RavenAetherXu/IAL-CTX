#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT/../.." && pwd)"
cd "$ROOT"

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  exit 1
}

printf 'CTX ctx-cli CI\n'

while IFS= read -r -d '' script; do
  python3 -m py_compile "$script"
done < <(find bin -maxdepth 1 -type f ! -name '*.cmd' -print0 | sort -z)
pass "py_compile bin/*"

python3 -m unittest discover -s tests -p 'test_*.py'
pass "unittest discover"

if grep -En 'default=["'\''](codex|lingxiaodian|huaguoshan|lingxiaodian:codex|huaguoshan-macos:codex)(-[^"'\'']*)?(:[^"'\'']*)?(/[^"'\'']*)?["'\'']' bin/ctx-route; then
  fail 'neutrality guard: ctx-route contains engine/device codename CLI default'
fi
if grep -En '\b(if|elif)\b[^#\n]*(==|!=)\s*["'\''](codex|ctx-codex-result|lingxiaodian:codex|huaguoshan-macos:codex)["'\'']' bin/ctx-route; then
  fail 'neutrality guard: ctx-route contains engine-name hard branch'
fi
if grep -Fq 'executed_by == "lingxiaodian:codex"' bin/ctx-route; then
  fail 'neutrality guard: ctx-route contains lingxiaodian:codex executed_by branch'
fi
if grep -Fq 'executed_by == "huaguoshan-macos:codex"' bin/ctx-route; then
  fail 'neutrality guard: ctx-route contains huaguoshan-macos:codex executed_by branch'
fi
if grep -Fq 'ALLOWED_TARGET_AGENTS' bin/ctx-lingxiao-agent; then
  fail 'neutrality guard: ctx-lingxiao-agent contains ALLOWED_TARGET_AGENTS'
fi
if grep -Fq 'ALLOWED_TARGET_AGENTS' bin/ctx-mac-codex-agent; then
  fail 'neutrality guard: ctx-mac-codex-agent contains ALLOWED_TARGET_AGENTS'
fi
pass "neutrality regression guard"

runtime_mac_agent="${CTX_CI_RUNTIME_MAC_AGENT:-}"
if [[ "${CTX_CI_CHECK_RUNTIME_SHA:-0}" != "1" ]]; then
  pass "runtime SHA gate skipped; set CTX_CI_CHECK_RUNTIME_SHA=1 to enable"
elif [[ "${CTX_CI_SKIP_RUNTIME_SHA:-0}" == "1" ]]; then
  pass "runtime SHA gate skipped by CTX_CI_SKIP_RUNTIME_SHA=1"
elif [[ -z "$runtime_mac_agent" ]]; then
  fail "runtime SHA gate: set CTX_CI_RUNTIME_MAC_AGENT when CTX_CI_CHECK_RUNTIME_SHA=1"
elif [[ -f "$runtime_mac_agent" ]]; then
  canonical_sha="$(sha256sum bin/ctx-mac-agent | awk '{print $1}')"
  runtime_sha="$(sha256sum "$runtime_mac_agent" | awk '{print $1}')"
  if [[ "$canonical_sha" != "$runtime_sha" ]]; then
    fail "runtime SHA gate: bin/ctx-mac-agent != $runtime_mac_agent"
  fi
  pass "runtime SHA gate"
else
  pass "runtime SHA gate skipped: $runtime_mac_agent not present"
fi

cd "$REPO_ROOT"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
  git diff --cached --check
  pass "git diff --check"
else
  pass "git diff --check skipped: not a git worktree"
fi
