> MIGRATED: canonical Secret Box now lives in <SECRET_BOX_REPO>. This copy is frozen history.

# SPEC: Secret Box v0 MVP（施工规约）

> 基准时间:2026-06-14
> 作者:PHAROS(ASC Pi @ 凌霄殿)
> 纲领:历史 Secret Box 白皮书(未随本仓打包)
> 冻结契约:`specs/Secret-Box-v0.md`(本规约是其可施工细化)
> 范围:最小可用经纪人。**不做**加密/轮换/vault/通用取值。

---

## 1. 目标与验收(MVP 完成的定义)

MVP 完成 = 下列**全部**通过(自动化测试):

- [ ] A1 未知动作被拒(`run <id> <未注册动作>` → 拒绝 + 审计)
- [ ] A2 未知/未批准调用者被拒
- [ ] A3 所有输出脱敏(密钥值在任何 stdout/日志/审计中均不出现)
- [ ] A4 每个动作发出一条审计事件(成功与失败都记)
- [ ] A5 审计记录为元数据,且 hash 链可校验(`audit --verify` 通过)
- [ ] A6 `require-xiao` 能力在无批准凭证时被拒、有凭证时放行,两种路径都入账
- [ ] A7 首批真实用例(搜索 key)端到端跑通:agent 永不见原值

## 2. 文件布局(v0 落点)

> 纪律:**先在 PHAROS 边界内做原型,跑通 A1–A7 后再上移 CTX 基质**(避免一上来动共享仓库)。
> 原型期路径(凌霄殿本地):

```
<SECRET_BOX_BASE>/
  registry.json          # 注册表(元数据,git 跟踪)
  ledger.jsonl           # 审计账本(hash 链 append-only,git 跟踪)
  recipes/               # 动作配方(每个能力一个,git 跟踪)
    brave-search.json
    tavily-search.json
  approvals/             # require-xiao 的批准凭证投放区(git 忽略)
  bin/secret-box         # 单文件 CLI(Python,对标 ctx-codex 风格)
```

上移目标(验收后):`ASC-Context-Engine/packages/secret-box/`。
**密钥值不在以上任何文件**;后端引用指向现有 `<SECRET_BACKEND>` 的键名。

## 3. 注册表 Schema（`registry.json`）

```json
{
  "version": "v0",
  "secrets": [
    {
      "secret_id": "brave-search",
      "label": "Brave Search API key",
      "capability": "web-search",
      "risk": "low",
      "backend": { "type": "local-config-key",
                   "ref": "<SECRET_BACKEND>#brave" },
      "allowed_actions": ["search"],
      "disallowed_actions": ["print", "get", "raw"],
      "approved_callers": ["pharos", "pi-agent"],
      "approval_policy": "auto-allow"
    }
  ]
}
```

字段约束:`backend.ref` 只存**键名引用**(`文件#键`),不存值。`approval_policy ∈ {auto-allow, require-xiao}`。

## 4. 动作配方（`recipes/<capability>.json`，broker-execute）

配方定义"盒内怎么执行",密钥占位符 `{{SECRET}}` 仅在 broker 进程内被替换:

```json
{
  "action": "search",
  "exec": {
    "kind": "http",
    "method": "GET",
    "url": "https://api.search.brave.com/res/v1/web/search?q={{q}}",
    "headers": { "X-Subscription-Token": "{{SECRET}}" },
    "redact": ["{{SECRET}}"],
    "return": "json"
  },
  "params": [{ "name": "q", "required": true, "max_len": 400 }]
}
```

执行规则:
- `{{SECRET}}` 从 `backend.ref` 现取现用,**仅存在于 broker 内存**,执行后立即丢弃。
- 返回前对 `redact[]` 与已知值做最终脱敏扫描(双保险)。
- 参数白名单校验(类型/必填/长度),拒绝注入。

## 5. CLI 契约（`bin/secret-box`）

```text
secret-box list                          # 列 secret_id + 能力 + 风险(无值)
secret-box describe <secret_id>          # 元数据详情(无值/无后端路径细节泄露)
secret-box run <secret_id> <action> [--param k=v ...] [--json]
                                         # 盒内执行,回脱敏结果
secret-box audit [--secret-id ID] [--since TIME] [--verify]
                                         # 审计查询;--verify 校验 hash 链
secret-box doctor                        # 自检:注册表合法/后端可达/账本完整/脱敏自测
```

**永不提供**:`get / print / cat / export / env`。`run` 的 action 必须在 `allowed_actions` 内。

## 6. 审计账本（`ledger.jsonl`,hash 链）

每行一条事件:

```json
{
  "audit_id": "sb_20260614T..._a1b2",
  "ts": "2026-06-14T...Z",
  "caller": "pharos",
  "ctx_ref": "task_or_route_id_or_null",
  "secret_id": "brave-search",
  "capability": "web-search",
  "action": "search",
  "result_status": "success|refused|error",
  "redaction_status": "clean|scrubbed",
  "artifacts": [],
  "prev_hash": "sha256(上一条)",
  "hash": "sha256(本条规范化 - 不含本字段)"
}
```

`audit --verify` 重算整链,任何断裂/篡改报错。链头哈希可 `doctor` 输出供 Xiao 外部留底。

## 7. 授权门（approval_policy）

- **auto-allow**:`caller ∈ approved_callers` 即放行。
- **require-xiao**:`run` 时检查 `approvals/<secret_id>/<nonce>.grant`(Xiao 投放的批准凭证,带过期时间)。
  - 无有效凭证 → `result_status: refused`,入账,告知"需 Xiao 授权"。
  - 有效凭证 → 放行,凭证标记已用,入账(记凭证 `grant_id`,不记内容)。
- **PHAROS 钩子**:能力 `modify-pharos` 注册为 `require-xiao`——这是 PHAROS 独立门控的落地。

## 8. 首批真实用例（验收负载)

Tier2 搜索 key 入列:`brave-search`(low/auto-allow)。
端到端:PHAROS 的 `web_search` 扩展改为调 `secret-box run brave-search search --param q=...`,
**扩展代码里不再出现 key**。验证 A3/A7:全程 grep 不到原值。

## 9. v0 明确不做(防镀金)

加密静存、轮换、多后端、跨设备 secret 协同、OS 级隔离、通用取值命令——全部 v1+。

## 10. 实施顺序

```
S1 registry.json + bin/secret-box(list/describe/doctor)         — 骨架
S2 broker-execute(run + recipe + 脱敏双保险)+ brave 配方         — 核心
S3 ledger.jsonl hash 链 + audit --verify                         — 不可抵赖
S4 approval_policy(auto-allow + require-xiao + grant 机制)        — 授权门
S5 A1–A7 自动化验收 + PHAROS web_search 接 brave 走盒              — 闭环
S6(验收后)上移 ASC-Context-Engine/packages/secret-box           — 正典化
```

每步独立可测、git 留痕。S1–S5 在 PHAROS 边界内,零跨仓风险。
