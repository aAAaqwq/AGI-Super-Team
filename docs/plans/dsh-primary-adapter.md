# 实施计划：DSH primary adapter

> **状态**：**草案，未实施**。需要明确批准后才会动代码。
>
> **2026-09-16 更新**：第 1 步「零成本验证」**已完成**，见下方
> [零成本验证结果](#零成本验证结果2026-09-16已完成)。结论改变了本计划的形态 ——
> 接入是**声明式 patch**，不是「与现有四个都不同的产物渲染路径」。
> 下方「核心设计问题：Agent 如何装配」一节中的方案 A/B/C 选型**已作废**。

目标：让 DeepSeek Harness (DSH) 成为第 5 个 primary harness，与 Claude Code / Codex / OpenClaw / Hermes 并列。

背景调研见 [DSH 装配](../researchs/adapter-dsh.md) 与 [Adapter 注册机制](../architecture/adapter-registration.md)。

## 零成本验证结果（2026-09-16，已完成）

在本机 `dsh` **0.1.5-rc.1** 上以 `DSH_HOME=/tmp/...` 隔离执行，**未触碰真实 `~/.dsh`**
（验证前后 `settings.yaml` / `.credentials.yaml` / `sessions` 时间戳均未变）。实测环境需从**中立目录**
启动 —— 从含 `.env` 的目录启动会被 DSH 的 launcher 安全检查拒绝（`only the launching environment may set`）。

| 验证项 | 结果 |
|---|---|
| `$DSH_HOME` 隔离 | ✅ 官方支持，优先级 `显式配置 > $DSH_HOME > ~/.dsh`（`dsh-home-paths/lib/index.js:65-73`） |
| 宿主 `agent-instructions` / `maxBytes` | ✅ 存在，`maxBytes: 65536` |
| **`skill-filesystem` / `tool-skill` 宿主层默认 `disabled: true`** | ✅ 证实 —— **技能不会自动生效** |
| 用户 patch 层位置 | ✅ **`$DSH_HOME/profiles/<profile>/cordis.patch.yml`**（`dsh-app-boot:313-314` `PROFILE_PATCH_FILENAME`） |
| **patch 能否启用被禁用的 `skill-filesystem`** | ✅ `disabled: false` 生效，dump 注脚显示 `patched by .../cordis.patch.yml` |
| **patch 能否配 `customSkillDirs`** | ✅ 生效，且 `roots.push(...)` 确认其直接进入技能根列表（`dsh-skill-filesystem:166`） |
| **`customSkillDirs` 运行时可达** | ✅ 探针技能出现在 headless 的 catalog 中 |
| **`~/.agents/skills`（rank 500）运行时可达** | ✅ 171 个真实技能被列出，含本仓库的 `orchestrate-agi-super-team` |
| `skillMode` 需要注意 | `headless` 的 `skill-filesystem` **默认启用**；`web` 默认禁用 —— 两个 profile 行为不同 |

**结论**：接入方式是**声明式用户 patch**，不需要 TypeScript 插件、不需要 `pnpm`、不需要复制 preset、
不需要 `!!js`。§4 的 `dsh.mjs` 实现规模因此从「核心工作量」降为「写一个 YAML patch + AGENTS.md 托管块」。

**仍待验证（不粉饰）**：未在真实用户 `~/.dsh` 上跑过；DSH 0.1.5-rc.1 官方明示会有破坏性变更；
`web` profile 下 patch 的运行时效果未观察（只验了 `headless`）。


## 为什么这不是一个小改动

「primary harness」在本仓库是**可执行的契约**，不是文档标签。`bin/installer/catalog.mjs` 对 `priorityHarnesses` 强制要求：

```js
tool.agentMode === "harness-adapter"
&& tool.runtimeEvidence === "pending"
&& tool.skillSource === "canonical-assigned"
&& typeof tool.adapterModule === "string"
&& typeof tool.connectionPath === "string"
```

且 `adapterModule` 必须**逐字等于** `bin/adapters/<id>.mjs`，路径不得越出 `bin/adapters/`。

## 需要改动的清单

### 1. 三处「恰好 18 个」硬约束 → 19

| 文件 | 行 | 内容 |
|---|---|---|
| `bin/installer/catalog.mjs` | 33 | `tools.length !== 18` → 抛错 |
| `tests/test_multi_cli_installer.py` | 112 | `test_adapter_manifest_has_exactly_eighteen_unique_tool_ids` |
| `tests/windows_cli_smoke.mjs` | 83 | `listedTools.length !== 18` |

**这三处必须同步修改**，否则 CI 失败。测试名中的 `eighteen` 也应改为 `nineteen`。

> 可选改进：把 18 抽成常量或从清单推导，避免下次再加目标时重复这个仪式。但这会扩大改动面，建议单独评估。

### 2. `config/cli-adapters.json` 新增条目

```json
{
  "id": "dsh",
  "label": "DeepSeek Harness",
  "scope": "global",
  "agentMode": "harness-adapter",
  "skillMode": "native",
  "agentPaths": ["..."],
  "skillPaths": ["skills/agi-super-team"],
  "support": "pending",
  "runtimeEvidence": "pending",
  "skillSource": "canonical-assigned",
  "adapterModule": "bin/adapters/dsh.mjs",
  "connectionPath": "agi-super-team/connection.json"
}
```

**待定**：`agentPaths` 的值。DSH 无 agent 文件目录（见下），这个字段填什么需要设计决策。

### 3. `bin/adapters/index.mjs` 注册

```js
import * as dsh from "./dsh.mjs";
const ADAPTERS = new Map([claudeCode, codex, openclaw, hermes, dsh].map(...));
```

### 4. `bin/adapters/dsh.mjs` 实现

必须导出：

| 导出 | 类型 | 用途 |
|---|---|---|
| `ADAPTER_ID` | `string` | `"dsh"` |
| `renderAdapterArtifacts` | `function` | 生成 DSH 原生产物 |
| `buildConnectionSpec` | `function` | 生成 `connection.json` |

**这是本计划的核心工作量**，因为 DSH 的 agent 模型与现有四个都不同。

### 5. `bin/installer/catalog.mjs` 的 `priorityHarnesses`

```js
const priorityHarnesses = new Set(["claude-code", "codex", "openclaw", "hermes", "dsh"]);
```

### 6. `config/harness-adapters/dsh.json` + `dsh.schema.json`

声明式接线契约，仿照现有四个的结构。

## 核心设计问题：Agent 如何装配

### 问题

现有四个 Adapter 都是「**每个角色一个原生文件**」：

| Adapter | 产物 |
|---|---|
| Claude Code | `~/.claude/agents/ast-ceo.md`（每角色一个 .md） |
| Codex | `~/.codex/agents/ast-ceo.toml`（每角色一个 .toml） |
| OpenClaw | 合并进 `openclaw.json` 的 `agents.entries` |
| Hermes | `$HERMES_HOME/skills/agi-super-team-agents/ast-*/SKILL.md` |

**DSH 没有 agent 文件目录。** 角色与指令只能通过 `AGENTS.md` 指令链注入：`$DSH_HOME/AGENTS.md`（全局）+ 项目链。

### 可选方案

**方案 A：单文件指令注入**
把 14 个 canonical 角色渲染成一段结构化的 `AGENTS.md` 内容，写入 `$DSH_HOME/AGENTS.md`。
- 优点：简单，符合 DSH 的唯一机制
- 缺点：丢失「每角色一个文件」的可发现性；与其它 Adapter 的产物形态差异大

**方案 B：Agent-as-Skill 降级**
把角色渲染成 DSH 技能（`skills/agi-super-team-agents/<role>/SKILL.md`），复用 DSH rank 400 技能根。
- 优点：复用现有 Agent-as-Skill 模式（本仓库 DeerFlow / WorkBuddy / CodeWhale 已有此模式）
- 缺点：角色变成"可加载的知识"而非"可委派的 agent"，层级语义弱化

**方案 C：指令 + 技能双写**
`AGENTS.md` 承担层级与路由说明，角色细节落在技能里按需加载。
- 优点：最贴近 DSH 的 progressive disclosure 设计
- 缺点：实现最复杂，需要设计两者的职责边界

**倾向方案 C**，但需要先确认 DSH 的 `AGENTS.md` 渲染预算（典型 65536 字节）是否够容纳 14 个角色的路由说明。

### 待确认的技术点

1. DSH 的 `AGENTS.md` 是否有 `maxBytes` 溢出风险
2. 目录型技能需要声明 `resourceBase`——本仓库技能多含 `references/`、`scripts/`，每个都要处理吗
3. DSH 项目的 `agentPaths` 字段语义（无 agent 目录时填什么）
4. `connection.json` 对 DSH 应记录什么

## 验证要求

实施后必须通过：

```bash
npm test                 # 含 19 个的新约束
npm run validate:strict
npm run check:architecture
```

并且**必须有真实客户端证据**，否则不能声称支持：

- [ ] 安装 DSH，观察 `~/.agents/skills/` 是否被发现
- [ ] 观察 `AGENTS.md` 是否被加载且未超预算
- [ ] 记录真实输出作为证据（当前 `runtimeEvidence: "pending"` 应保持 pending，直到有 canary 证据）

## 建议的推进顺序

1. **先做零成本验证**：装 DSH，确认它能否读到现有 `~/.agents/skills/`。这不需要改任何代码。
2. **据结果选方案**：若技能层已通，剩 agent 层，按 A/B/C 选型。
3. **再动契约**：确认投入后，一次性改完三处 18 约束 + Adapter 模块。

第 1 步完成后应回来更新本计划。

## 相关文档

- [DSH 装配机制](../researchs/adapter-dsh.md)
- [Adapter 注册机制](../architecture/adapter-registration.md)
- [各 Coding Agent 装配总览](../researchs/README.md)
