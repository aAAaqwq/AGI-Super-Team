---
name: agi-super-team-orchestrator
description: 使用 Hermes Profiles 与 Kanban 按意图路由到主责 C-suite；需要跨职能并行、独立复核或完整团队交付时使用。禁止默认 CTO。
metadata:
  hermes:
    category: orchestration
    tags: [agi-super-team, profiles, kanban]
    requires_toolsets: [kanban]
---

# AGI Super Team｜Hermes Orchestrator

runtimeEvidence: pending

开始前先读取 `../agi-super-team/orchestrate-agi-super-team/SKILL.md`，并按需读取其 references。canonical Skill 决定是否组队、通用任务包、Governor 与人工批准契约；本 Skill 只补充 Hermes Profile、Kanban 与 delegation 方式。

## 意图路由（先选主责，禁止默认 CTO）

先识别工作对象与交付物，再选主责 C-suite。单一领域任务直接调用对应角色，不要先找 CEO。

| 意图信号 | 主责 | 可协作 | 典型关键词 |
|---|---|---|---|
| 产品方向、用户问题、需求边界、优先级、体验与可访问性 | CPO（`cpo`） | CRO、CTO | 产品、需求、用户、体验、优先级、功能范围、PRD、可用性、信息架构 |
| 技术战略、架构边界、接口/API、技术选型、性能与可靠性 | CTO（`cto`） | PE、CDO | 架构、技术选型、API、接口、可靠性、性能、故障复盘、系统设计、平台成本 |
| 已批准设计的跨模块实现、集成、测试、评审与可回退交付 | PE（`pe`） | CTO | 实现、编码、集成、测试、重构、缺陷修复、交付、代码评审 |
| 量化假设、回测、模型评估、策略与组合风险 | CQO（`cqo`） | CDO、CFO | 量化、回测、策略、因子、模型评估、组合风险、交易信号、A股、选股 |
| 市场定位、品牌、获客、投放、SEO 与归因 | CMO（`cmo`） | CCO、CRO | 品牌、获客、投放、广告、SEO、定位、增长实验、归因、渠道 |
| 预算、单位经济、定价证据、资本配置与成本 | CFO（`cfo`） | CPO、CQO | 预算、定价、单位经济、成本、现金流、融资、资本配置、财务预测 |
| 数据契约、口径、质量、血缘、指标体系与分析模型 | CDO（`cdo`） | CRO、CTO | 数据口径、指标、数据质量、血缘、数据治理、分析模型、报表、数据安全 |
| 内容策略、选题、脚本结构、平台适配与制作编排 | CCO（`cco`） | CMO、CRO | 内容、选题、脚本、短视频、公众号、小红书、抖音、B站、编辑简报、平台适配 |
| 合同、隐私、跨境合规、许可、知识产权与监管 | CLO（`clo`） | CDO、CFO | 合同、隐私、合规、许可、知识产权、监管、条款、数据跨境 |
| 研究问题设计、一手证据、竞品与市场情报、多源核验 | CRO（`cro`） | CDO、CCO | 研究、证据、竞品、情报、调研、核验、市场扫描、事实核查 |
| 客户发现、资格审查、赢单策略、方案叙事与销售管道 | CSO（`cso`） | CPO、CFO | 销售、客户、商机、赢单、投标、方案、管道、续约、客户成功 |
| 运营计划、责任与依赖、SOP、产能、排期与异常恢复 | COO（`coo`） | CPO、CFO | 运营、SOP、流程、排期、产能、跨部门、执行节奏、责任矩阵、异常恢复 |
| 重大结论、发布、资金、法律、安全或完成声明的独立复核 | Governor（`governor`） | — | 复核、放行、审计、风险升级、完成声明、发布前检查、独立验证 |

只在以下任一条件成立时升级到 CEO（`ceo`）：
- 任务同时覆盖两个以上 C-suite 领域，且需要取舍或统一交付
- 需要在稀缺资源、预算、范围与时间之间做公司级决策
- 多个 C-suite 结论冲突，需要综合并保留异议
- 用户明确要求 CEO 或公司级团队

兜底：意图仍不明确时先提出一个澄清问题；不要默认调用 CTO，也不要在没有跨领域证据时启动 CEO。

## 触发条件

当任务需要一个以上持久命名 C-suite 角色、独立 Governor 复核，或需要跨 Profile 保留可观察的依赖与交接时使用。

## 核心约束

1. 持久命名角色必须通过 **Profiles + Kanban** 路由。先从真实 Profile roster 确认 assignee 存在；蓝图文件不等于已创建 Profile。
2. 不要调用或发明 `delegate_task(profile=...)`。Hermes 的 `delegate_task` 不承担命名 Profile 路由。
3. `delegate_task` 只用于 Manager Profile 内需要推理的匿名短任务；默认使用 leaf，不得把匿名结果宣称为某个 ast-* Profile 的持久产出。
4. 标准 Team 深度上限为二、每个 Manager 最多两个并发匿名子任务。叶子和 Governor 不得继续委派。
5. Manager 工作完成后再让独立 `ast-governor` Profile 复核；CEO 综合任务同时依赖 Manager 产出和 Governor 复核。
6. 未经人类批准，不创建 Profile、Cron 或 Gateway，不启动 Kanban dispatcher，不执行发布、部署、资金、账号或不可逆操作。

创建工作卡时，通过 `kanban_create` 的 `skills` 数组固定装载与 assignee 同名的角色 Skill（例如 assignee 为 `ast-cto` 时至少传入 `ast-cto`）。再按 connection spec 追加该角色分配的 canonical Skills。Governor 卡必须固定装载 `ast-governor`，CEO 综合卡必须固定装载 `ast-ceo`；仅写 assignee 而不装载角色 Skill，不算完成角色接线。

## Kanban 依赖模板

- `manager-output`：分配给一个已确认存在的 Manager Profile。
- `governor-review`：分配给 `ast-governor`，父依赖为 `manager-output`。
- `ceo-synthesis`：分配给 `ast-ceo`，依赖 `manager-output` 与 `governor-review`。

如果 Hermes CLI、Profile、Gateway 或 Kanban dispatcher 不可用，停止自动调度，返回缺失项并采用人工/顺序回退；不得伪造 canary 或 receipt。

## Persistent Profile 索引

- `ast-ceo`：仅当任务跨两个以上 C-suite 领域、需要在资源/预算/范围/时间之间取舍，或多个专业结论冲突需要综合时调用；用户明确要求 CEO 或公司级决策也算。典型信号：公司级、跨职能、资源取舍、路线图、最终决策。
- `ast-cto`：需要技术战略选择、架构边界划分、接口/API 设计评审、技术选型对比、平台成本评估、系统可靠性设计或故障复盘时调用。典型信号：架构、技术选型、API/接口、性能、可靠性、故障复盘、系统设计。
- `ast-pe`：已批准的设计需要跨模块实现、集成、测试、代码评审、缺陷修复或可回退交付时调用。典型信号：实现、编码、集成、测试、重构、缺陷修复、交付。
- `ast-cpo`：需要产品方向取舍、用户问题定义与需求澄清、体验与可访问性评审、优先级排序或可验证需求拆解时调用。典型信号：产品、需求、用户、体验、优先级、PRD、功能范围。
- `ast-cqo`：需要量化假设设计、回测与复现、模型评估与独立复核、组合风险控制或实验预登记时调用。典型信号：量化、回测、策略、因子、A股、选股、组合风险。
- `ast-cmo`：需要市场定位与品牌策略、渠道增长实验、付费投放或 SEO 方案、获客测量与归因设计时调用。典型信号：品牌、获客、投放、广告、SEO、定位、归因。
- `ast-cfo`：需要预算与滚动预测、单位经济与定价证据、资本配置取舍、财务控制或成本优化时调用。典型信号：预算、定价、单位经济、成本、现金流、融资。
- `ast-cdo`：需要数据契约与口径定义、数据质量与血缘治理、指标体系或分析模型设计、数据安全架构评审时调用。典型信号：数据口径、指标、数据质量、血缘、数据治理、报表。
- `ast-cco`：需要内容策略与编辑简报、平台内容适配、选题与脚本结构设计、内容制作编排或来源与权利审查时调用。典型信号：内容、选题、脚本、短视频、公众号、小红书、抖音、B站。
- `ast-clo`：需要合同与协议风险评审、隐私与跨境合规检查、许可与知识产权问题识别、监管政策适用判断时调用。典型信号：合同、隐私、合规、许可、知识产权、监管。
- `ast-cro`：需要研究问题设计、一手证据获取与核验、竞品或市场情报扫描、多源证据综合与不确定性说明时调用。典型信号：研究、证据、竞品、调研、核验、市场情报。
- `ast-cso`：需要客户发现与资格审查、赢单策略、方案与投标叙事、销售管道分析或客户成功交接设计时调用。典型信号：销售、客户、商机、赢单、投标、管道。
- `ast-coo`：需要运营计划与执行节奏、责任与依赖映射、跨部门流程与 SOP 设计、产能规划或异常恢复安排时调用。典型信号：运营、SOP、流程、排期、产能、跨部门。
- `ast-governor`：需要独立复核重大结论、发布、安全、资金、法律或完成声明，并给出放行门决定或风险升级时调用。典型信号：复核、放行、审计、风险升级、完成声明。

## Selected Specialist Skills

- 本次未选择 specialist Skill。
