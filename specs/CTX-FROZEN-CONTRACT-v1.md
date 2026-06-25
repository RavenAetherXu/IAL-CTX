# SPEC: CTX Neutral-Hub FROZEN CONTRACT v1

> **STATUS: FROZEN — 2026-06-22.** 这是中立化(R-D 解绑)期间两端 Codex 的**唯一实现依据**。
> 任何一端不得自行发明不兼容的 profile/动词/词表。改契约必须先回到本文件、人类批准、再实现。
> 来源固化自:`CTX-neutral-hub.md`(v0.1 已交叉评审)+ `CTX-capability-vocab.md`(freeze-draft)+
> `CTX-STAGE-REVIEW-2026-06-22.md`(R-D 风险与 Track A 任务)。
> 回档点:tag `milestone-ctx-known-good-20260622`(运行时 + 规范仓)。

---

## 1. 不变量(必须满足,否则不算完成)

1. **数据层已中立,保持**:账本接受任意 `agent_id/device_id/target_agent` 自由字符串,无白名单。
2. **两级身份**:`agent_key`(稳定、换引擎不变)/ `agent_id=<device>:<engine>`(可变,display/provenance)。
   路由、租约、审计绑 `agent_key` + capabilities;`agent_id` 仅展示。
3. **单写不变量**:所有 claim 经唯一常驻凌霄殿账本,`flock(LOCK_EX)` + 状态 CAS + `atomic_write`。
   远端 agent 永不直写账本(FRP-first 代理到凌霄殿)。账本不得置于网络挂载。
4. **每步保绿**:任何改动后,现有正/反向 codex+pi 路由必须仍 verified;`milestone` tag 可回档。
5. **default-deny secret 门**:`secret_capabilities` 缺省=未知=拒绝,直到 Secret Box 存在。

---

## 2. `ctx-agent-profile-v1`(冻结 schema)

自助注册对象,append-only,**latest-wins per `agent_key`**。经 `ctx-route agent-register` 写入。

```json
{
  "schema": "ctx-agent-profile-v1",
  "agent_key": "huaguoshan/local-pi",
  "agent_id": "huaguoshan-macos:pi",
  "device_id": "huaguoshan-macos",
  "engine": { "name": "pi", "version": "0.78.1", "model": "claude-opus-4.8" },
  "kind": "executor",
  "capabilities": ["os.macos","runtime.pi","exec.shell","fs.read","probe.read-only","net.frp","transport.file-drop"],
  "constraints_supported": ["read_only_first","no_secrets"],
  "transports": ["frp-reverse-ssh:127.0.0.1:6022","home-file-drop"],
  "availability": "intermittent",
  "audit_profile": {
    "result_link_kind": "ctx-pi-reply-v1",
    "expects_thread_id": false,
    "ephemeral_session": true
  },
  "secret_capabilities": [],
  "registered_at": "ISO8601Z",
  "red_lines": ["metadata_first","no_secret_values"]
}
```

- **first-writer-pins-key**:`agent_key` 首次注册记录 `device_id`+transport 来源;后续 rebind 必须同源,否则拒绝/标记(Secret Box 前为标记)。
- `audit_profile.result_link_kind` 取值:codex→`ctx-codex-result`(`expects_thread_id:true`);pi→`ctx-pi-reply-v1`;未知→**strict 默认**。

---

## 3. 执行器适配器契约(冻结 4 动词)

```
register()      -> 发布 ctx-agent-profile-v1(kind=executor)+ capabilities
claim(route)    -> 仅当 eligible(route, self);原子 claim+lease;绝不双 claim
execute(route)  -> 在本端自身权限上下文执行
reply(route)    -> metadata-first:status, summary, evidence, artifacts,
                   secret_events, residual_risk, next_action
```

适配器可互换。现有脚本收敛为已注册适配器,**行为不变**:
`ctx-codex`(codex)/`ctx-pi-worker`·`ctx-lx-worker`(pi)/`ctx-huaguoshan-frp-agent`(只读探针)。
新 agent 只写 1 个适配器(实现 4 动词)+ 1 个 profile 即加入,**零引擎改动**。

---

## 4. `eligible()`(冻结撮合谓词,替代白名单)

```
eligible(route, agent) :=
    route.target_site            == agent.device_id
 && route.status                 == "queued"
 && route.required_capabilities  ⊆ agent.capabilities
 && route.constraints            ⊆ agent.constraints_supported
 && (route.required_engine 缺省 OR
       (agent.engine.name == route.required_engine.name
        AND semver(agent.engine.version) >= semver(route.required_engine.version_min)))
 && (not route.approval_required  OR agent approval-capable)
 && route.secret_capabilities == []          (Secret Box 前硬性 default-deny)
```

- `target_agent` 降为 **advisory**;命名定向仍兼容,但不再必需。
- 多 agent 同时 eligible → **first-atomic-claim-wins**(flock/CAS 仲裁),v0 无打分。
- 未知 capability token(不在 §6 词表)→ 路由 **unroutable(loud)**,绝不静默 eligible。

---

## 5. `audit_profile` 评估规则(冻结,替代 doctor 名字硬编码)

- **claim-time pinning**:doctor 评估**认领时刻**快照到 route 上的 audit_profile 版本,**非最新**。
- **checked,not trusted**:doctor 校验**实际 reply 形状**匹配声明的 `result_link_kind`,不采信自述。
- **strict 默认 + 不可自我静默**:未知/缺失 audit_profile → strict(warn-on-missing,loud)。
  `ephemeral_session` 只能把"缺 session"降级为 INFO,**不得**压制 reply-shape / evidence 检查。
- **删除**:`ctx-route` 中 `executed_by == "lingxiaodian:codex"` / `"huaguoshan-macos:codex"` 字面量分支
  (R-D1),改为按 `agent_key` 查 audit_profile 跑通用检查。

---

## 6. capability 词表 v0(冻结,引用 `CTX-capability-vocab.md`)

命名扁平可枚举 `<facet>.<token>`,presence-only 集合成员匹配。版本/精度走 `required_engine` 结构谓词,**不进 token**。
token 集见 `CTX-capability-vocab.md §2`;首 4 agent 能力见 §4。控制词表:表外 token → unroutable(loud)。

---

## 7. 租约 / 自动回收(冻结)

- claim 写 `lease.expires_at`(`--lease-seconds`,默认 1200s,可按 route 覆盖)。
- 通用 reaper 必须 `requeue` 满足 `lease_expired()` 的 route → 回 `queued`,防卡死 executor 占用。
- requeue 清 lease、`retry_count++`;`retry_count >= max` → expire(留证据)。

---

## 8. 验收(全部满足才算 Track A 完成)

1. `ctx-route` 非测试路径**无任何 agent 名字面量**(`grep -c 'lingxiaodian:codex' ctx-route` 非测试→0)。
2. 两端白名单删除(R-D2 `ctx-lingxiao-agent:52/241`、R-D6 `ctx-mac-codex-agent:62/282`),改 `eligible()`。
3. 两端 `AGENT_ID` 写死常量(R-D7)→ 从 profile 读取/注册。
4. 新一次性 `echo-agent` 仅 `agent-register` 即跑通一条 route 全生命周期,**零引擎改动**。
5. agent 换引擎(新 `agent_id`、同 `agent_key`)保留路由与审计连续性。
6. 现有正/反向 codex+pi 路由保持 verified。
7. **Shadow E2E(影子跟踪)双端实战验证通过**(见 §9)。

---

## 9. Shadow E2E(影子跟踪法)验收协议

> 目的:在不影响真实协作的前提下,**在实战中**验证两端中立化后的 CTX 稳定可靠可用。

- **影子路由**:打 `shadow:true` 标记的真实生命周期 route,与真路由同引擎、同账本、同 doctor,
  但 summary/artifact 标注为 smoke,不进入真业务。
- **双端覆盖**:正向(凌霄殿→花果山)+ 反向(花果山→凌霄殿)各跑影子全链路
  `register→queued→eligible-claim→execute→reply→verify→doctor`。
- **中立性断言**:其中至少一条影子路由由一个**未硬编码进任何脚本的临时 agent_key**
  (echo-agent / shadow-probe)凭 capability 认领,证明"按能力非按名"。
- **稳定性断言**:并发影子 claim 无双 claim;租约过期被 reaper 回收;doctor 全绿。
- **通过判据**:两端影子路由 verified + doctor 0 critical + 中立性断言成立。出一份
  `docs/reports/CTX-SHADOW-E2E-*.md`。

---

## 10. 纪律

- 接口冻结 = 本文件。两端**并行**改各自侧,但都对齐本文件。
- **Go 重写**:本契约(§2-§7)全部冻结且 §8 验收通过前,**绝不开始 Go 编译**。
- 每步前确认 `milestone-ctx-known-good-20260622` tag 在;改坏可
  `git checkout milestone-ctx-known-good-20260622 -- bin/` 或解压物理备份回档。
