# CTX 全局状态梳理(2026-06-22,凌霄殿 Fable)

> 用户复述的本质原则:**CTX = 不绑定任何模型/任何 agent 的"信息高速公路",通用基础设施,
> 新老 agent 都能自主注册使用。** 本文核对实际状态对不对得上这个原则。

## 0. 一句话本质(spec 已锁)
```
FRP connects. CTX coordinates. Secret Box authorizes. Local agents execute. Humans audit.
                    ▲ 中立                                   ▲ 可插拔
```
CTX 只负责**协调**(谁该做什么、账本、路由),不负责执行,也不该认识具体是谁在执行。

## 1. 运行时现状(file-backed,v0.1)
- 运行时 `<CTX_BASE>`:`shared/state.json`(任务账本)、`routes/`、`scopes/`、`agents/profiles/`、`devices/`、`bin/`(12 个活脚本)。规范仓 `<CTX_REPO>`(specs/ + packages/ + runtime/)。
- 链路活着:今天(06-22)还有 `route_..._hgs_live-concerto-smoke` [replied];FRP 反隧道 OK(frps active / 6022 listening)。
- 两个 codex 协作史(runtime git):pi<->pi worker、反向 poller、FRP claimant、agent-registry、lease-reaper —— 凌霄殿 codex + 花果山 codex 经 FRP 双向推进过(主线机体锻打 / Session 分析专线 / 舰队评审),多数 route 现 [blocked]=done。
- 任务账本:45 总 / 30 成功 / 余 blocked·timeout·failed(Secret Box S1 blocked、若干 review timeout)。

## 2. 对照你的原则:打分卡
### ✅ 已中立(符合原则)
- **数据层本就中立**:账本接受任意 `agent_id/device_id/target_agent` 为自由字符串,**无白名单**;任何 agent 都能在数据层注册、claim。
- **设计已锁原则**:`specs/CTX-neutral-hub.md`(凌霄殿 Fable,2026-06-15,draft v0)开宗明义"CTX 必须是中立协调 hub,不是 codex 工具也不是 pi 工具;任何 agent 自助注册、按能力路由(非按名)、换引擎仍能协作"。
- **自助注册已落第一步**:`bin/ctx-agent-registry`(neutral self-describing,`ctx-agent-profile-v1`)+ 已注册 4 个 profile(lingxiaodian/primary-reasoner、lingxiaodian/codex-bridge、huaguoshan/local-pi…)。两级身份:`agent_key`(稳定)/`agent_id=<device>:<engine>`(可变,换模型不断链)。**ADDITIVE、独立、暂未并入热路径**。

### ❌ 仍耦合(违背原则,待拆)
| # | 耦合 | 实证(file:line) | 应改为 |
|---|---|---|---|
| C1 | doctor 按 agent 名硬判审计 | `ctx-route:2510` `if executed_by=="lingxiaodian:codex"` / `:2529` `=="huaguoshan-macos:codex"` | 读 profile 的 `audit_profile`,数据驱动 |
| C2 | claimant 写死目标白名单 | `ctx-lingxiao-agent:52` `ALLOWED_TARGET_AGENTS={"codex","ctx-codex","local-native"}` + `:241` 强制 | 按 `capability` 匹配(`eligible()`),非按名 |
| C3 | 无执行器抽象/能力路由 | `required_capabilities` 记录了但路由仍主要按名;无通用 matchmaker | 执行器适配器契约(register/claim/execute/reply 四动词)+ 能力撮合 |

> 即:**本质对、数据层对、设计对、注册第一步对;但"控制面热路径"还认识具体 agent 名字。** 这就是理想与现状的差距。

## 3. bin/ 现状 = 一堆"按设备/引擎"的脚本
`ctx-lingxiao-agent / ctx-mac-agent / ctx-mac-codex-agent / ctx-huaguoshan-pi-bridge / ctx-pi-worker / ctx-lx-worker / ctx-lx-reverse-poller / ctx-huaguoshan-frp-agent` —— 当前是**每个 agent 一个专属脚本**。
spec 的方向:把它们收敛成**可互换的"执行器适配器"**(各自实现 4 动词 + 发布 profile),新 agent 只写一个适配器 + 一个 profile 即可加入,**零引擎改动**。

## 4. 迁移路径(spec §7,增量不破坏)
1. 加 `agent-register` + profile 存储(已做第一步:ctx-agent-registry)。
2. 把 codex/pi(LX)/pi(HGS)/frp-probe 注册成 profile → 行为不变。
3. doctor 改读 `audit_profile`(删 C1 字面量)。
4. claimant 改用能力 `eligible()`(删 C2 白名单)。
5. 加通用能力 matchmaker;`target_agent` 降为 advisory。
6. **中立验收测试**:一个一次性 `echo-agent` 仅靠注册 profile 即可加入协作、零引擎改动。

## 5. 与 Go 重写的关系(spec §8,关键纪律)
> **中立 hub 契约必须在 Go 重写之前冻结。执行器接口里还嵌着 codex/pi 名字时,绝不开始 Go 编译。**
Python 阶段:定义并稳定 {agent profile, executor adapter, capability routing} → 用 codex+pi+一个新 agent 验证 → 冻结接口 → 再 Go 编译 ctx-route。

## 6. 验收标准(spec §10)
- `ctx-route` 非测试代码路径**无任何 agent 名字面量**。
- 新 agent 仅 `agent-register` 即可协作,零引擎改动。
- agent 换引擎(新 `agent_id`、同 `agent_key`)仍保留路由与审计连续性。
- 现有 codex+pi 正反向 route 保持 verified/green。

## 7. 结论 + 建议下一步
- **你的原则没跑偏,而且已是 CTX 的成文设计**;现状是"数据层+设计+注册"已中立,**热路径 C1/C2/C3 三处名字耦合未拆**。
- 这正是 ASC 1.0 把 CTX 从"两个 codex 的私有桥"升级为"通用 agent 基础设施"的核心工程。
- 建议顺序(增量、每步保绿):**先做 spec §7 第 2-4 步(注册全部现有 agent → doctor 读 audit_profile 删 C1 → claimant 改能力匹配删 C2)**,再加 matchmaker(C3),最后跑 echo-agent 中立验收 → 然后才谈 Go 冻结。
- 额度:codex 受限期内,这些拆耦合是**纯 Python additive 改造**,凌霄殿本地就能推,不必等花果山 codex。
