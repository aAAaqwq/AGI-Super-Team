---
name: agi-super-team-orchestrator
description: 使用 Hermes Profiles 与 Kanban 路由 AGI Super Team
metadata:
  hermes:
    category: orchestration
    tags: [agi-super-team, profiles, kanban]
    requires_toolsets: [kanban]
---

# AGI Super Team｜Hermes Orchestrator

runtimeEvidence: pending

开始前先读取 `../agi-super-team/orchestrate-agi-super-team/SKILL.md`，并按需读取其 references。canonical Skill 决定是否组队、通用任务包、Governor 与人工批准契约；本 Skill 只补充 Hermes Profile、Kanban 与 delegation 方式。

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

- `ast-ceo`：需要拆解公司级或跨职能目标、在多个 C-suite 之间取舍、配置稀缺资源、选择最小充分团队、安排独立复核并综合成最终决策时调用。
- `ast-cto`：需要技术战略选择、架构边界划分、接口/API 设计评审、技术选型对比、平台成本评估、系统可靠性设计或故障复盘时调用。
- `ast-pe`：已批准的设计需要跨模块实现、集成、测试、代码评审、缺陷修复或可回退交付时调用。
- `ast-cpo`：需要产品方向取舍、用户问题定义与需求澄清、体验与可访问性评审、优先级排序或可验证需求拆解时调用。
- `ast-cqo`：需要量化假设设计、回测与复现、模型评估与独立复核、组合风险控制或实验预登记时调用。
- `ast-cmo`：需要市场定位与品牌策略、渠道增长实验、付费投放或 SEO 方案、获客测量与归因设计时调用。
- `ast-cfo`：需要预算与滚动预测、单位经济与定价证据、资本配置取舍、财务控制或成本优化时调用。
- `ast-cdo`：需要数据契约与口径定义、数据质量与血缘治理、指标体系或分析模型设计、数据安全架构评审时调用。
- `ast-cco`：需要内容策略与编辑简报、平台内容适配、选题与脚本结构设计、内容制作编排或来源与权利审查时调用。
- `ast-clo`：需要合同与协议风险评审、隐私与跨境合规检查、许可与知识产权问题识别、监管政策适用判断时调用。
- `ast-cro`：需要研究问题设计、一手证据获取与核验、竞品或市场情报扫描、多源证据综合与不确定性说明时调用。
- `ast-cso`：需要客户发现与资格审查、赢单策略、方案与投标叙事、销售管道分析或客户成功交接设计时调用。
- `ast-coo`：需要运营计划与执行节奏、责任与依赖映射、跨部门流程与 SOP 设计、产能规划或异常恢复安排时调用。
- `ast-governor`：需要独立复核重大结论、发布、安全、资金、法律或完成声明，并给出放行门决定或风险升级时调用。

## Selected Specialist Skills

- 本次未选择 specialist Skill。
