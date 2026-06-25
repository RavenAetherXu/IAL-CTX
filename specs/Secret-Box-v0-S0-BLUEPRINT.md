> MIGRATED: canonical Secret Box now lives in <SECRET_BOX_REPO>. This copy is frozen history.

# SPEC: Secret Box v0 — S0 蓝图（语言无关施工靶图）

> 基准时间:2026-06-15
> 作者:PHAROS(ASC Pi @ 凌霄殿)
> 上游:历史 Secret Box 白皮书(未随本仓打包)· `specs/Secret-Box-v0.md`(冻结契约)· `specs/Secret-Box-v0-MVP.md`(施工序列)
> 本文定位:把白皮书四件硬物 + 授权门**固化为可直接编码的契约**——三套 schema 定稿 + recipe 模板 + `run` 控制流伪码 + 脱敏/hash 链/授权门机制 + A1–A7 测试矩阵。
> 性质:**纯设计,零系统变更,零跨仓风险**。定稿后 Go 实现或 Codex 施工都以本文为唯一靶子。
> 边界:本文不含任何密钥值/哈希/前后缀。

---

## 0. 语言裁决（已定）

- 实现语言:**Go**(单包,纯标准库优先:`net/http crypto/sha256 os/exec encoding/json flag`)。
- 依据:契约已冻结 + 跨设备授权基质定位 + 单一可信二进制;详见语言决策讨论。
- v0 不引入第三方依赖(密钥经纪人最小化供应链面)。sqlite 不用——审计走 JSONL hash 链。
- 原型落点(凌霄殿本地,验收前):`<SECRET_BOX_BASE>/`;验收后上移 `ASC-Context-Engine/packages/secret-box/`。

---

## 1. 核心不变量（所有实现必须满足）

```
INV-1  密钥值只在 secret-box 进程内存中存在,执行后立即清零;绝不进入 agent 进程/stdout/stderr/审计/会话。
INV-2  无任何 get/print/cat/export/env 命令;run 的 action 必须 ∈ allowed_actions。
INV-3  凡离开 broker 的字节(stdout/stderr/error/artifact)都必经脱敏双扫。
INV-4  每个 run 动作(成功/拒绝/错误)都写且只写一条审计事件,元数据-only。
INV-5  审计账本 append-only + hash 链;任何断裂/篡改被 audit --verify 检出。
INV-6  registry / recipe / ledger 三类文件永不含值/哈希/前后缀/私钥体/含密钥命令行。
```

---

## 2. 目录布局（v0 原型）

```
<SECRET_BOX_BASE>/
  registry.json          # 注册表(元数据,git 跟踪)
  recipes/               # 动作配方(每能力一个,git 跟踪)
    call-model.json
  ledger.jsonl           # 审计账本(hash 链 append-only,git 跟踪)
  approvals/             # require-xiao 批准凭证投放区(git 忽略)
    <secret_id>/<nonce>.grant
  state/                 # 运行态(链头缓存、grant 已用标记;git 忽略)
  bin/secret-box         # 单一 Go 二进制(源码 src/ 同仓)
```

后端密钥仍在既有 `<SECRET_BACKEND>`;registry 只存键名引用。

---

## 3. Schema 定稿

### 3.1 注册表 `registry.json`

```jsonc
{
  "version": "v0",
  "secrets": [
    {
      "secret_id": "zenmux",                       // 唯一 ID
      "label": "ZenMux model gateway key",         // 人读标签(无值)
      "capability": "call-model",                  // 对应 recipes/<capability>.json
      "risk": "medium",                            // low|medium|high
      "backend": {
        "type": "local-config-key",               // v0 唯一后端类型
        "ref": "<SECRET_BACKEND>#zenmux"   // 文件#键名,绝不含值
      },
      "allowed_actions": ["call-model"],
      "disallowed_actions": ["print", "get", "raw", "export"],
      "approved_callers": ["pharos", "pi-agent"],
      "approval_policy": "auto-allow"              // auto-allow|require-xiao
    }
  ]
}
```

字段约束:
- `secret_id` 全局唯一,`^[a-z0-9][a-z0-9-]*$`。
- `backend.ref` 形如 `path#key`,**只引用键名**。
- `approval_policy ∈ {auto-allow, require-xiao}`。
- `risk ∈ {low, medium, high}`。
- 禁止出现:`value/secret/hash/prefix/suffix/token` 等疑似值字段(doctor 扫描拒绝)。

### 3.2 配方 `recipes/<capability>.json`

```jsonc
{
  "action": "call-model",
  "exec": {
    "kind": "http",                                // v0: http | exec
    "method": "POST",
    "url": "https://zenmux.ai/api/v1/chat/completions",
    "headers": { "Authorization": "Bearer {{SECRET}}",
                 "Content-Type": "application/json" },
    "body": "{\"model\":\"{{model}}\",\"messages\":[{\"role\":\"user\",\"content\":\"{{prompt}}\"}]}",
    "redact": ["{{SECRET}}"],                      // 声明需脱敏的占位符
    "return": "json"                               // json|text
  },
  "params": [
    { "name": "model",  "required": false, "max_len": 80,   "default": "anthropic/claude-..." },
    { "name": "prompt", "required": true,  "max_len": 4000 }
  ]
}
```

占位符规则:
- `{{SECRET}}` 仅由 broker 在内存内替换为 `Backend.Resolve(ref)` 的值;替换只发生在 header/body/url 组装的最后一刻。
- `{{param}}` 由 `--param k=v` 提供,先过白名单校验(类型/必填/max_len)再替换;拒绝未声明参数。
- `kind: exec` 形态:密钥经 **env 注入**(`{{SECRET}}` → 环境变量),**绝不进 argv**;命令模板用 `argv[]` 数组,不走 shell 字符串拼接。

### 3.3 审计事件 `ledger.jsonl`（每行一条）

```jsonc
{
  "audit_id": "sb_20260615T120000Z_a1b2",
  "ts": "2026-06-15T12:00:00.000Z",
  "caller": "pharos",                  // 断言式(--caller/env),用于归因
  "ctx_ref": "task_or_route_id_or_null",
  "secret_id": "zenmux",
  "capability": "call-model",
  "action": "call-model",
  "result_status": "success",          // success|refused|error
  "refuse_reason": null,               // refused 时填枚举:unknown-action|unknown-caller|no-grant|bad-params
  "approval": { "policy": "auto-allow", "grant_id": null },  // require-xiao 时记 grant_id,不记内容
  "redaction_status": "clean",         // clean|scrubbed
  "artifacts": [],                     // 产物路径(无值)
  "prev_hash": "sha256-of-previous-line",
  "hash": "sha256( prev_hash + canonical(event_without_hash) )"
}
```

**不记**:值、前后缀、值哈希、原始 config dump、含密钥命令行、HTTP 响应体原文(只记状态/产物路径)。

---

## 4. `run` 控制流（伪码,实现的唯一权威）

```
secret-box run <secret_id> <action> [--param k=v ...] [--caller C] [--ctx-ref R] [--json]

func Run(secretID, action, params, caller, ctxRef):
    entry := registry.Lookup(secretID)
    if entry == nil:               audit(refused, "unknown-secret"); exit 2
    # A2 调用者门
    if caller ∉ entry.approved_callers:
                                   audit(refused, "unknown-caller"); exit 3
    # A1 动作门
    if action ∉ entry.allowed_actions OR action ∈ entry.disallowed_actions:
                                   audit(refused, "unknown-action"); exit 3
    # A6 授权门
    grant := nil
    if entry.approval_policy == "require-xiao":
        grant = approvals.FindValid(secretID)        # 未过期 & 未用
        if grant == nil:           audit(refused, "no-grant"); exit 4
    recipe := recipes.Load(entry.capability)
    if !recipe.ValidateParams(params):               # 类型/必填/max_len/未声明
                                   audit(refused, "bad-params"); exit 5

    # ▶ 进入密钥临界区(仅此刻、仅本进程内存)
    secret := backend.Resolve(entry.backend.ref)     # []byte
    defer wipe(secret)                               # INV-1 用完即焚
    req := recipe.Assemble(secret, params)           # {{SECRET}}/{{param}} 替换
    out, err := recipe.Execute(req)                  # http 或 exec(env 注入)

    # ▶ 离开临界区前:脱敏双扫(INV-3)
    cleanOut, scrubbed := redact(out, secret, recipe.redact)
    cleanErr, _        := redact(err, secret, recipe.redact)

    if grant != nil: approvals.MarkUsed(grant)       # 一次性
    audit(statusOf(err),                             # success|error
          redaction = scrubbed ? "scrubbed":"clean",
          grant_id  = grant?.id)
    print(cleanOut)                                  # agent 只见脱敏结果
    exit statusCode(err)
```

错误路径同样过脱敏后才入账/输出。任何 panic 的兜底 handler 也必须脱敏。

---

## 5. 脱敏引擎（双保险）

```
func redact(data []byte, secret []byte, declared []string) ([]byte, scrubbed bool):
    out := data; scrubbed := false
    # 第一层:声明占位符对应的已解析值
    # 第二层:已解析密钥真值的逐字节扫描(防 recipe 漏声明)
    for token in union(declared-resolved-values, [secret]):
        if bytes.Contains(out, token):
            out = bytes.ReplaceAll(out, token, "***REDACTED***")
            scrubbed = true
    # 同时扫描 base64/url-encoded 变体(防编码绕过)— v0 至少覆盖 base64std/url
    for variant in encodings(secret):
        if bytes.Contains(out, variant):
            out = bytes.ReplaceAll(out, variant, "***REDACTED***"); scrubbed = true
    return out, scrubbed
```

铁律:stdout / stderr / error message / artifact 写盘内容,全部过 `redact` 才出盒。`scrubbed=true` 表示触发了兜底——如实记 `redaction_status: scrubbed`,不隐藏。

---

## 6. Hash 链（账本不可抵赖）

```
canonical(event) = JSON(event 去掉 "hash" 字段, 键字典序, 无空格, UTF-8)
hash(event)      = hex(sha256( prev_hash + canonical(event) ))
prev_hash(第一条) = "GENESIS"

写入:flock(ledger.jsonl) → 读末行取 prev_hash → 计算 hash → append 一行 → 缓存链头到 state/head.json
audit --verify:prev := "GENESIS"; for each line: 重算并比对 line.hash 与 line.prev_hash; 任一不符 → exit 非零 + 指出行号
doctor 输出当前链头 hash,供 Xiao 外部留底比对(防账本自身被悄改)
```

---

## 7. 授权门（auto-allow / require-xiao）

```
auto-allow:    caller ∈ approved_callers 即放行(已在 §4 A2 覆盖)。
require-xiao:  grant 文件 approvals/<secret_id>/<nonce>.grant
  grant schema(Xiao 投放):
    { "grant_id":"g_...", "secret_id":"...", "issued":"...Z",
      "expires":"...Z", "max_uses":1, "issued_by":"xiao" }
  FindValid:存在 & now < expires & 已用次数 < max_uses。
  MarkUsed:在 state/grants-used.jsonl 追加 {grant_id, used_at}(一次性/计数)。
  审计只记 grant_id,不记文件内容。
PHAROS 门控落地:capability "modify-pharos" 注册为 require-xiao →
  Codex 每次介入 PHAROS 都需 Xiao grant 且入不可抵赖账本。
v0 诚实标注:caller 为断言式归因,非密码学认证;grant 签名校验留 v1。
```

---

## 8. CLI 契约

```
secret-box list                          # secret_id + capability + risk(无值)
secret-box describe <secret_id>          # 元数据详情(不泄后端路径细节/值)
secret-box run <secret_id> <action> [--param k=v ...] [--caller C] [--ctx-ref R] [--json]
secret-box audit [--secret-id ID] [--since TIME] [--verify]
secret-box doctor                        # 注册表合法/后端键名可达/账本链完整/脱敏自测/链头输出
```

退出码:`0` 成功 · `2` 未知 secret · `3` 门拒(动作/调用者) · `4` 无 grant · `5` 参数非法 · `1` 执行错误。
**永不实现**:`get/print/cat/export/env`。

---

## 9. A1–A7 验收测试矩阵（自动化,MVP 完成定义）

| ID | 断言 | 测试方法 | 期望 |
|----|------|---------|------|
| A1 | 未知动作被拒 | `run zenmux raw` | exit 3 · 审计 refused/unknown-action · 无值输出 |
| A2 | 未知调用者被拒 | `run zenmux call-model --caller stranger` | exit 3 · refused/unknown-caller |
| A3 | 全输出脱敏 | 注入回显密钥的 mock 后端,`run` | stdout grep 不到真值 · redaction_status=scrubbed |
| A4 | 每动作一条审计 | 任意 run 前后 `wc -l ledger.jsonl` | 恰好 +1 |
| A5 | hash 链可校验 | `audit --verify`;再手改一行重验 | 干净链 pass;篡改 fail+行号 |
| A6 | require-xiao 双路径 | 无 grant→拒;投 grant→放行;两次都查账本 | 各一条审计,grant 路径记 grant_id |
| A7 | 端到端不见原值 | 全链路 `grep -r <真值>` 于 stdout/ledger/会话导出 | 0 命中 |

测试形态:Go `testing` + 一个 `mock-echo` 后端配方(故意回显密钥,专测 A3/A7)。`make accept` 一键跑 A1–A7,全绿 = MVP 完成。

---

## 10. 施工序列映射（S0 → S6）

```
S0 本蓝图(契约冻结)                                   ← 当前
S1 registry 加载 + CLI(list/describe/doctor)+ Backend  骨架   A1/A2 雏形
S2 broker run + recipe(http)+ 脱敏双扫 + call-model    核心   A3/A7
S3 ledger hash 链 + audit --verify                     不可抵赖 A4/A5
S4 approval 门(auto-allow + require-xiao + grant)      授权门  A6
S5 make accept 跑 A1–A7 + PHAROS 调模型/搜索接盒        闭环
S6 验收后上移 packages/secret-box                       正典化
```

S1–S5 全在凌霄殿本地原型边界内,零跨仓风险;A1–A7 全绿后再上移。

---

## 11. 待 Xiao 拍板的开口项

- **D2 首批负载**:本蓝图默认用现有 `zenmux` key 做 `call-model`(不依赖补新 key)。若坚持原 brave 用例,需先补 `api_keys.json#brave`。
- **B1 Go 工具链**:`go` 当前未安装,装 Go 属系统状态变更,需 Xiao 批准后执行。
- **D3 施工方**:PHAROS 直接写 / 派 Codex 写 + PHAROS 逐 artifact 验收。

> 本蓝图一经确认即为 v0 实现的唯一权威契约;后续任何偏离须改本文并 git 留痕。
