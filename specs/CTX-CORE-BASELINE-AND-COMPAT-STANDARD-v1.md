# CTX 核心通路基准线 + 跨版本兼容标准 v1

> **STATUS: 基准线(BASELINE),变更受控。** 这是 CTX 作为"跨端基建/运河"的宪法级文档。
> 立项缘起:2026-06-22 一整轮跨端改造(中立化解绑 + lease 修复 + FRP-first cutover + 统一看板)
> 暴露的真实失败,提炼为标准。**任何后续维护/迭代必须围绕本基准线。**
> 作者:凌霄殿 Fable。

---

## 0. 第一性原理:运河不可截流

跨端产品的**核心挑战不是功能,是"两端更新进度不一时仍稳定互通"**。

> 红线:**一端更新,绝不能让另一端连不上、协议不匹配、甚至老端口直接报废。**

把通信系统看作**一条跨时空的运河 / 神经枢纽**:可以升级路面材质、优化通行量,
但**河道本身永不被打破、永不被截流**。治病不能因小感冒就开膛破肚——**局部更新,不动全局**。

判据:**极客实验可容忍反复崩;生产端崩一次=失信任。** 故核心通路 = 最高谨慎,热迭代层 = 可快。

---

## 1. 三层工程分层(分清核心资产 vs 热迭代)

| 层 | 是什么 | 变更纪律 |
|---|---|---|
| **L-CORE 核心内核(运河本体)** | 任务发放/领取生命周期、账本 schema、租约/认领原子语义、传输可达契约、单一真相源 | **受控**:必须向后兼容 + 兼容证明 + 双端 skew 测试 |
| **L-ADAPTER 可插拔适配器** | 执行器(codex/pi/probe/frp-claimant)、传输(FRP/file-drop)、claimant | 符合 L-CORE 契约即可换;**换不破核心** |
| **L-ITERATE 热迭代层** | 看板/观测/UX、matchmaker 策略、doctor 规则、capability 词表(**加法**) | 自由快迭代,**不得触碰 L-CORE 语义** |

### 1.1 L-CORE 不变量清单(无论怎么更新都必须绝对稳定)
1. **路由生命周期五动词语义**:`create → claim → start → reply → verify` 的状态机与含义不变。
2. **账本 envelope 必填字段**:`route_id / status / origin_site / target_site / created_at` 等核心字段**只增不删不改义**。
3. **认领原子性**:单一 VPS 账本 + `flock(LOCK_EX)` + 状态 CAS;first-atomic-claim-wins;绝不双 claim。
4. **租约归属语义**:claim 产生 lease;start/reply/verify 必须证明归属(agent/instance/lease)。
5. **传输可达契约**:ledger 是单一真相源(VPS);"连得上 + 能登账 + 能回执"语义与传输实现解耦。
6. **白盒可审**:每条路由两端可见、origin→executor 可追溯(见 §6)。

> L-CORE 改动 = 基准线评审。**接口里嵌具体 agent/引擎名字 = 违反中立**(见 `CTX-FROZEN-CONTRACT-v1.md`)。

---

## 2. 跨版本兼容铁律(本标准的核心,直接解决"一端更新搞死另一端")

基于本轮真实失败提炼。**所有 L-CORE / L-ADAPTER 改动必须遵守:**

- **R1 加法不减法(additive-only)**:字段/动词/token 只增,不删、不改义。删除或改义 = 破坏性变更,需基准线评审 + 迁移窗口 + 双端同步计划。
- **R2 新强制必带兜底(graceful enforcement)**:引擎新增的校验,对**不提供新字段的旧客户端**必须**回落到等价旧校验**,不得硬拒。
  - 范例(本轮 B0):start/reply 新增 lease_id 强制 → 旧客户端不传 lease_id 时,回落到 agent/instance 归属校验,而非 `lease_id mismatch` 直接拒。
- **R3 词表/能力协商,不假设(negotiate, don't assume)**:`required ⊆ caps` 类匹配,词表演进**只能 additive**;新端不得用旧端不认的 token 去寻址旧端;两端按**能力交集**工作。
- **R4 寻址向后兼容**:advisory 字段(如 `target_agent=capability`)**不得让旧端的必填解析失败**;旧端按名、新端按能力,**共存**。
- **R5 版本声明 + 能力降级**:profile/route 带 `schema` 版本;两端探测彼此能力,按**最小公共能力集**协作,绝不假设对端已升级。
- **R6 默认拒绝只用于安全门**:default-deny 仅用于 secret/授权(`secret_capabilities`);**不得**用 default-deny 去拒绝"仅仅是旧版本"的对端。
- **R7 老通路保活**:迁移期间(如 FRP-first cutover),旧通路在新通路验证通过前**不停用、不报废**;cutover 必须可一键回退。

---

## 3. 变更受控矩阵(对症下药,不重修整条路)

| 改动落在 | 准入条件 |
|---|---|
| **L-CORE** | ① 基准线评审 ② **兼容证明**(老端不破:新引擎×旧客户端 + 旧引擎×新客户端 skew 测试)③ 单测覆盖兼容回落 ④ 双端 live 验证 ⑤ 可回退锚点 |
| **L-ADAPTER** | ① 符合 L-CORE 契约 ② 单测 ③ 双端 live ④ 备份+回退 |
| **L-ITERATE** | ① 纯加法 ② 单测 ③ 不碰 L-CORE 语义 |

> 纪律:**改 L-CORE/claimant 行为的任务,验收必须包含"更新并跑绿对应单测 + skew 测试",不能只靠 live 路由实测**(本轮测试债的根因)。

---

## 4. 具身失败经验登记(Embodiment Failure Log → 标准条目)

| # | 真实失败(本轮) | 根因 | 沉淀标准 |
|---|---|---|---|
| F1 | 引擎加严格 lease 强制 → 6-14 旧客户端 reply 被拒("一端更新搞死另一端"原型) | 新强制无兜底 | **R2**(graceful enforcement)+ B0 修复模式 |
| F2 | 新词表 token(os.macos)≠ 旧客户端 CAPABILITIES(macos) → 路由被静默跳过 | 词表代次漂移 | **R3**(词表 additive + 协商) |
| F3 | `target_agent=capability` 被旧名字白名单拒 | 寻址不向后兼容 | **R4**(寻址向后兼容,advisory 共存) |
| F4 | 路由在两端面板均不可见(三碎片观测面) | 白盒未进核心契约 | **§6 白盒不变量** + 统一看板 |
| F5 | 单测打 packages/bin 副本、全程只靠 live 验证 → 代码与测试静默漂移 | 测试未跟契约 | **§5 skew/CI 门** + §3 验收纪律 |
| F6 | 误发新词表 token 给旧固定探针 + 发错通道(账本轮询 vs 文件投递) | 通道/契约认知不清 | **§1 分层 + R5 能力探测** |

---

## 5. 兼容性测试要求(skew testing,防"一端更新另一端崩")

- **跨版本 skew 矩阵(强制)**:对每个 L-CORE 改动,至少验证四象限的关键路径仍互通或优雅降级:
  - 新引擎 × 新客户端 ✓
  - **新引擎 × 旧客户端**(最关键:R2 回落)✓
  - 旧引擎 × 新客户端 ✓
  - 旧引擎 × 旧客户端 ✓
- **单测必须覆盖兼容回落**(如:不传 lease_id 仍能 start;旧 token 仍可路由)。
- **最小 CI**:push 即跑 `unittest`,red 即挡;单测指向规范仓 `bin` 且要求 PR 同步更新测试。
- 单一真相源:测试断言"当前契约行为",契约变 → 测试同步变(变更同一 PR)。

---

## 6. 白盒不变量(产品信任的地基)

- **每条路由两端可见可审**:`ctx`(任一端)默认显示统一通行看板:发起 origin → 执行 executor + 状态 + 传输 + 时长。
- **可追溯**:trace_id 串联;evidence/artifact/verdict 留痕;无 trace 的行动不存在。
- **白盒 ≠ 全景监控**:分域、最小披露(产品多租户期);但"自己的协作流量自己看得见"是底线。

---

## 7. 当前各层归属(快照,指导后续)

- **L-CORE(受控)**:`ctx-route`(账本/生命周期/lease/CAS)、route envelope schema、FRP-first 单一真相源。
- **L-ADAPTER**:`ctx-codex` / `ctx-lingxiao-agent` / `ctx-huaguoshan-frp-agent`(VPS侧认领) / Mac `ctx-mac-codex-agent`·`ctx-mac-agent`·`ctx-pi-worker` / `ctx-hgs`。
- **L-ITERATE**:统一看板渲染、matchmaker 策略、doctor 规则、capability 词表(additive)。

---

## 8. 立即应用(把本标准用到手头任务)

1. **测试债清偿**:更新 9 个旧单测 → 断言**新按能力行为** + 新增 **skew 回落断言**(R2:不传 lease_id 仍 start;R3:旧 token 仍可路由)→ 88 全绿 + 加最小 CI。
2. **双端 live 实战**:新引擎×当前客户端跑通稳定协作 + 质量可靠 + 白盒看板两端可见。
3. 之后任何改动:先判定落在哪层 → 按 §3 矩阵准入 → §5 skew 测试 → 才合并。

> 一句话:**先冻结运河(L-CORE 不变量 + 兼容铁律),再在路面上自由施工(L-ITERATE)。** 这是 CTX 从"极客实验"走向"可信生产基建"的分水岭。
