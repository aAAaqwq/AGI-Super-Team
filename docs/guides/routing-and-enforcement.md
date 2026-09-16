# 路由分级与强制层

> 本文回答两个问题：**任务如何被路由到 agent**，以及**哪些约束真的被强制、哪些只是提示词**。
> 配套阅读：[Team/Subagent/Skill 连接原理](team-agent-skill-architecture.md)（构建时编译与运行时流动）、[四框架 Adapter 手册](harness-adapters.md)（安装与接线）。

---

## 一、四层架构总览

```
① 内容层    skills/ + agents/                    最外层产物
              ↑
② 契约层    config/*.json                        唯一事实来源（手工维护，唯此处）
              ↑
③ 分发层    bin/installer/render.mjs + bin/adapters/*.mjs    编译器
              ↓
④ 运行时层  各家 harness 的原生机制              路由 + 强制
```

| 层 | 唯一事实来源 | 产物 |
|---|---|---|
| **① 内容** | `skills/*/SKILL.md`、`agents/<role>/*.md` | 可执行的方法包与角色契约 |
| **② 契约** | `config/team-manifest.json`（14 个顶层角色）<br>`config/<role>-specialists.json`（92 个叶子）<br>`config/agent-hierarchy.json`（谁管谁 + 深度）<br>`config/cli-adapters.json`（18 个安装目标）<br>`config/harness-adapters/<harness>.json`（各家执行契约） | 结构化 JSON，被校验脚本强制 |
| **③ 分发** | `bin/installer/render.mjs`（文案与格式的唯一来源）<br>`bin/adapters/<harness>.mjs`（18 个编译器） | 各家原生文件 |
| **④ 运行时** | 各 harness 自己的配置 | 路由与强制行为 |

**关键设计**：内容文案**只在契约层写一次**，由 `render.mjs` 统一渲染。
改一处模板 → 所有 harness 同时生效（例：`canonicalAgentDescription()` 改一次，Claude Code / Codex / Hermes / OpenClaw 四家全变）。

### 角色清单（契约层）

```
ast-ceo            唯一公司级协调者
├─ 11 个 C-suite    cto(22 叶子) cco(19) cfo(8) cso(8) cmo(7)
│                   cro(6) clo(6) cdo(5) cqo(4) coo(4) cpo(3)
├─ ast-pe          工程实现负责人（跨模块交付）
└─ ast-governor    独立证据复核者
                   叶子合计 92
```

### 分发目标（18 家）

| harness | agents 落点 | skills 落点 |
|---|---|---|
| claude-code | `.claude/agents/` | `.claude/skills/` |
| codex | `.codex/agents/*.toml` | `.agents/skills/` |
| hermes | `skills/agi-super-team-agents/` | `skills/agi-super-team/` |
| openclaw | `agency-agents/agi-super-team/` | `skills/agi-super-team/` |
| copilot / cursor / gemini-cli / qwen / kiro / qoder / opencode / trae / antigravity / deerflow / workbuddy / codewhale | 各自 `.xxx/agents` | 各自 `.xxx/skills` |
| aider / windsurf | `CONVENTIONS.md` / `.windsurfrules` | —（仅规则文件） |

---

## 二、路由分级 L0–L3

**先判级，再路由。级定错，后面全错。**

| 级别 | 判据 | 路由 |
|---|---|---|
| **L0 单点** | 单一领域、一步可完成 | 主会话直接做，或调 **1 个**最匹配叶子 |
| **L1 单域多步** | 单一领域、需专业执行 | 主会话 → **该域 C-suite** → 1–2 个叶子 |
| **L2 跨职能** | 涉及 **≥2 个** C-suite 领域 | 主会话 → **ast-ceo** → 多个 C-suite → 各自叶子 |
| **L3 重大** | 发布 / 资金 / 法律 / 安全 / 完成声明 | 同 L2，且**必须**追加 `ast-governor` 独立复核 |

### 核心规则

1. **L0 和 L1 不经过 `ast-ceo`。** CEO 只处理跨职能与公司级议题，**不是所有任务的必经节点**。
2. **L2 才启用 CEO** 做目标拆解与 C-suite 选择。
3. **L3 必须调 `ast-governor`**；被审方不能自证；未经复核不得对外作完成声明。
4. 叶子不得再派发；需要拆分的子任务向上抛给所属 C-suite。
5. 判级不确定时**按更低级别起手**；一旦发现涉及第二个 C-suite 领域，立即升到 L2。

### 例子

| 任务 | 判级 | 路由 |
|---|---|---|
| 「把 5minbtc 的 `vol_gate` 死字段删掉」 | **L0** | 主会话直接做 —— **不叫任何 ast agent** |
| 「审一下这个 PR 的安全性」 | **L1** | `主会话 → ast-cto → ast-cto-security-engineer`（**不过 CEO**） |
| 「评估新品定价，并调研目标市场」 | **L2** | `主会话 → ast-ceo → {ast-cfo → pricing-analyst, ast-cro → trend-researcher}` |
| 「轮换 API key 后发版」 | **L3** | L2 路径 **+ ast-governor 独立复核** 后才能作发布声明 |

---

## 三、强制层：哪些是真强制，哪些只是提示词

这是本文最重要的部分。**两家主力框架的能力形状一致：**

> **「深度 / 叶子边界」可硬强制；「路由」两家都只能靠提示词或自写 hook。**

| 契约项 | Claude Code | Codex | 硬度 |
|---|---|---|---|
| **叶子禁止派发** | `disallowedTools: Agent`（frontmatter 黑名单） | 由 `max_depth` 自然导出 | **硬** |
| **深度上限** | `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=3` | `[agents] max_depth = 3` | **硬** |
| **并发上限** | `env.CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=6` | `[agents] max_threads = 12` | **硬（但全局）** |
| **每-manager 并发 ≤2** | 做不到（只有会话级全局） | 做不到（只有全局 `max_threads`） | **做不到** |
| **路由分级 L0–L3** | `~/.claude/CLAUDE.md` | `~/.codex/AGENTS.md` | **软（提示词）** |
| **谁能调谁**（manager→叶子白名单） | 无声明式机制 | 无声明式机制 | **软 / 需自写 hook** |
| **L3 强制 governor 复核** | 无原生门 | 无原生门 | **软 / 需自写 hook** |

### 关于"软"的诚实说明

官方文档明确：CLAUDE.md 与 AGENTS.md 都是**上下文，不是强制层**——
> "Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a `PreToolUse` hook instead."（Claude Code）
> "Direct system/developer/user instructions … take precedence over AGENTS.md instructions."（Codex）

**要把"软"变成"硬"，唯一路径是自写 `PreToolUse` hook**（两家都支持 `exit 2` / `permissionDecision: "deny"`）。

### Codex 的一个特殊机制

Codex 内置的 spawn 门是「**仅当用户明确要求子代理/委派/并行时才允许 spawn**」。
而 `~/.codex/AGENTS.md` 以 **user 角色**注入 —— 因此**那张 L0–L3 分级表本身就是这次授权**。没有它，Codex 侧的路由根本不会触发。

---

## 四、当前实测落地状态（2026-09-15）

| 项 | Claude Code | Codex |
|---|---|---|
| 14 个顶层角色 description | ✅ 任务式 + 「不适用」边界 | ⚠️ **角色尚未安装** |
| 92 个叶子 | ✅ 已装（94 个含 `disallowedTools`）| ⚠️ **未安装** |
| 深度 | ✅ `=3` | ✅ `max_depth = 3` |
| 并发 | ✅ `=6` | ✅ `max_threads = 12` |
| 路由分级规则 | ✅ `~/.claude/CLAUDE.md` | ✅ `~/.codex/AGENTS.md` |
| 审计 hook | ✅ 已装，**实测触发过** | ⏸ 未装（需交互式 `/hooks` 信任） |
| 验证级别 | 运行时验证 | **仅"配置被接受"**（本机无 auth） |

### 已知缺口

1. **Codex 侧 106 个角色全部不存在** —— `~/.codex/agents/` 为空，`config.toml` 无 `[agents.<name>]`。AGENTS.md 里点名的角色当前无法解析。
2. **审计 hook 在 Codex 侧未装** —— 需在 `/hooks` 交互式 review 并记录信任 hash；且 0.139.0 不读 `~/.codex/hooks.json`，必须写进 `config.toml`。
3. **`scripts/build_codex_csuite_adapter.py` 是另一条 Codex 路径** —— 它的插件 payload 描述仍从 `focus` 派生，未吃到 `trigger` 改造。
4. **per-manager 并发**两家都做不到，契约里的 `maxConcurrentChildren: 2` 目前**无法硬强制**，只能靠提示词。

---

## 五、字段字典：description 是怎么生成的

顶层角色（`team-manifest.json → agents[]`）与叶子（`<role>-specialists.json`）的 description 均由 `render.mjs` 渲染：

```
<name>｜<trigger> 不适用：<doNotUseWhen>
```

| 字段 | 语义 | 反例（**不要**这么写） |
|---|---|---|
| `trigger` | **任务形态**：什么时候该调用它 | 「负责技术战略与架构边界」——这是职责，不是触发条件 |
| `doNotUseWhen` | **真正的不适用条件**：什么时候不该用它 | 「制定技术方向和约束」——这恰恰是 CTO 的本职 |
| `boundary` | 范围 + 交接（**不渲染进 description**，仅供生成文档用）| — |

**为什么这很重要**：早期版本用模板 `` `任务主要属于 ${name} 的职责范围时调用。${focus}` `` 渲染，
造成了**循环定义**——要知道"是否属于 CTO 职责范围"才能决定该不该调用 CTO，而那正是它该帮你判断的。
结果：**入口层不触发，整个团队跑不起来**。现已改为任务式 `trigger`，并把错放在「不适用：」后面的 `boundary` 换成真正的 `doNotUseWhen`。

---

## 六、相关文档

- [Team/Subagent/Skill 连接原理](team-agent-skill-architecture.md) — 构建时编译、运行时流动、五类连接的唯一事实来源
- [四框架 Adapter 手册](harness-adapters.md) — 统一安装流程、落盘路径、权限与委派边界
- [框架机制参考](../../skills/orchestrate-agi-super-team/references/framework-mechanisms.md) — 各框架官方机制与证据等级
