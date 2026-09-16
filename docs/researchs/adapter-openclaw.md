# OpenClaw 装配

> **证据等级说明**：`[官方]` = OpenClaw 官方文档；`[实测]` = 在本机 OpenClaw 2026.6.8 (844f405) 上实际执行命令验证；`[推定]` = 由官方材料推论；`[无法证实]` = 官方文档与实测均未能确认。
> 本文件于 2026-09-16 按官方文档（docs.openclaw.ai）逐条核实，`[社区]` 标注的条目已重新定级。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| 插件安装 | `openclaw plugins install <pkg>` | `[官方]` + `[实测]` |
| 插件源 | 显式 locator 选源：`clawhub:` / `npm:` / `git:` / `npm-pack:` / `--marketplace` / 本地路径·压缩包；**裸包名**回退序为 内置插件 id → 官方目录 → npm（**ClawHub 不在裸名回退链上，须显式写 `clawhub:`**） | `[官方]` |
| 原生插件清单 | `openclaw.plugin.json`（含内联 JSON Schema，即使配置为空） | `[官方]` |
| 兼容 bundle | 其它生态的 manifest 格式由 OpenClaw **自动探测** | `[官方]` |
| 查看 | `openclaw plugins list [--enabled] [--verbose] [--json]` | `[官方]` + `[实测]` |
| 检查 | `openclaw plugins inspect <name> [--json] [--runtime]`（`inspect` 与 `info` 同义） | `[官方]` + `[实测]` |

### 逐条核实说明

**1. `plugins install`** —— 命令存在且语义已确认。官方原话为「Install a plugin or hook pack (path, archive, npm spec, git repo, `clawhub:package`, or marketplace entry)」，参数是一个 `path-or-spec-or-plugin`。
`[实测]` `openclaw plugins install --help` 输出与上述一致（本机 2026.6.8）。支持 `.zip` / `.tgz` / `.tar.gz` / `.tar` 压缩包；原生插件的压缩包**必须**在解压根含有效 `openclaw.plugin.json`，只有 `package.json` 的压缩包会在写入安装记录前被拒。

**2. 插件源优先级 —— 原表述已修正。** 原文「ClawHub → npm → git → 本地目录 → 压缩包」把并列的源写成了优先级链，官方文档中**不存在这样一个阶梯**。正确语义是：
- 用 `clawhub:` / `npm:` / `git:` / `npm-pack:` **显式前缀**确定性选源；
- **裸包名（无前缀）** 的回退序只有三级：① 命中内置（bundled）插件 id → 用内置副本；② 命中官方外部插件 id → 用官方目录；③ 其余裸包名 → 走 npm。Raw `@openclaw/*` 命中内置插件时同样先解析到内置副本。
- ClawHub 是社区插件的**主要发现面**（`openclaw plugins search`），但**不在裸名回退链上**——要装 ClawHub 包必须写 `clawhub:`。
- git / 本地路径 / 压缩包 / marketplace 是**并列的可选源**，不是回退链的后几级。

**3. `openclaw.plugin.json` —— 由 `[社区]` 升级为 `[官方]`。** 官方《Plugin manifest》页明确：每个原生 OpenClaw 插件**必须**在插件根放置 `openclaw.plugin.json`；OpenClaw 读取它以**在不执行插件代码的前提下**校验配置；缺失或无效的清单会阻断配置校验并被当作插件错误。「每个插件都必须携带 JSON Schema，即使它不接受任何配置；空 schema 合法（如 `{ "type": "object", "additionalProperties": false }`）」——原文「含内联 JSON Schema，即使配置为空」属实。必填键为 `id` 与 `configSchema`。

**4. 其它生态 manifest 由 OpenClaw 自动探测 —— 由 `[社区]` 升级为 `[官方]`，且给出了确定的探测顺序（见下文「兼容 bundle 与自动探测」）。**

**5. `plugins list` / `plugins inspect`** —— 两条命令均存在，参数已核实。
`[实测]`：`openclaw plugins list --enabled --verbose` 输出 72 个插件及 `format:` / `source:` / `origin:` / `version:` 明细；`openclaw plugins list --json` 输出可解析 JSON。`--enabled` 只显示已启用项，`--verbose` 从表格切换为逐插件明细，`--json` 为机器可读清单（含 registry 诊断与依赖解析状态）。
`[实测]`：`openclaw plugins inspect|info [id]` 支持 `--json`、`--runtime`、`--all`。`--runtime` 会加载插件模块并报告已注册的 hooks / tools / commands / services / gateway methods / HTTP routes；不带 `--runtime` 时只做冷清单与注册表检查。

**6. 技能根与 agent 目录的官方依据 —— 需补限定条件（见「本仓库的装配方式」）。**

### 配置与状态

| 项目 | 路径 | 覆盖变量 | 证据 |
|---|---|---|---|
| 配置 | `~/.openclaw/openclaw.json`（JSON5） | `OPENCLAW_CONFIG_PATH` | `[官方]` |
| State | `~/.openclaw` | `OPENCLAW_STATE_DIR` | `[官方]` |
| Home | （仅作为内部路径默认值的基准，非独立目录） | `OPENCLAW_HOME` | `[官方]` |

配置里的关键节点：`models.providers`、`agents.defaults`、`agents.entries.*`。`[官方]`

> **`agents.list` 与 `agents.entries` —— 原文标记已修正。** 官方文档（Multi-agent routing、Agent runtime、Skills、Multi-agent sandbox and tools）通篇使用 **`agents.entries.*`**；`agents.list` 是**旧版 roster 结构**，由 `openclaw doctor --fix` 迁移为带键的 `agents.entries`（官方 changelog 与 issue 中均可见 "Moved agents.list to keyed agents.entries."）。
> `[实测]`：本机 2026.6.8 上 `openclaw config get agents.entries --json` 返回空，而 `openclaw config get agents.list --json` 返回天枢 agents 数组——该版本 schema 仍以 `agents.list` 为实际键。**因此原文写 `agents.list` 对本机版本是对的，但不能当成跨版本契约**；迁移后需改写为 `agents.entries`。
> `[推定]`：`agents.list` 是即将/正在被替换的旧结构，`agents.entries` 是目标结构。Adapter 的 `connection.listPath = "agents.list"` 因此是一个**版本相关假设**，跨版本健壮性存疑。

### Agent 机制

- 每个 agent 有独立 workspace 与 `agentDir` `[官方]`
- **Agent 身份文件 —— 原文有误，已修正。** 官方文档中 **不存在 `agent.md` 这个身份文件**。每个 agent 的身份是 **workspace 目录**里的一组 bootstrap Markdown（`AGENTS.md` / `SOUL.md` / `IDENTITY.md` / `USER.md` / `BOOTSTRAP.md` / `MEMORY.md`），在**新会话第一轮**被注入 system prompt 的 Project Context。`[官方]`
  `[实测]`：本机 `~/.openclaw/agents/main/agent/` 下只有 `models.json` 与 `openclaw-agent.sqlite*`，**没有 `agent.md`**；全树扫描 `~/.openclaw/agents/**/agent.md` 结果为空。
  > 流传的「`~/.openclaw/agents/<agent-id>/agent.md`」说法只见于第三方站（meta-intelligence.tech）与社区仓库，**无官方依据**。原文的 `[社区]` 现降为 `[无法证实]`。
- workspace 里可放 `SOUL.md`、`AGENTS.md`、可选 `USER.md` `[官方]`（完整清单另含 `IDENTITY.md`、`BOOTSTRAP.md`、`MEMORY.md`）
- 子 agent 通过 `agents.entries.<id>.subagents.allowAgents` 授权白名单 `[官方]`
  > 注意：`allowAgents` **只支持 per-agent 写法**（旧结构下为 `agents.list[].subagents.allowAgents`），**不能**写在 `agents.defaults.subagents` 下，否则配置校验失败、Gateway 启动崩溃（官方 issue #11982）。
- `sessions_spawn` 工具负责派生 `[官方]`

## 本仓库的装配方式

**走安装器，不用插件形态**：

```bash
npx -y agi-super-team@latest --tool openclaw --install --connect
```

- Agent 产物：`<当前配置目录>/agency-agents/agi-super-team/ast-*`
- 技能产物：`<当前配置目录>/skills/agi-super-team/<skill>`
- `--connect` 先 dry-run，再按 `id` 合并 `agents.list`，**保留非托管 Agent**，不创建 channel binding

#### 这两条路径的官方依据（原文标 `[官方]`，实际为部分成立）

**技能根 `…/skills/agi-super-team/<skill>` —— 官方依据成立，但有前提。**
官方《Skills》给出托管技能根为**第 4 优先级 `…/skills`**，并注明 `openclaw skills install --global` 正是装进 `~/.openclaw/skills`。分组布局被明确支持：「只要 `SKILL.md` 出现在配置根之下就会被发现（**最多 6 层深**）」，示例即 `<root>/skills/personal/foo/SKILL.md`；`skills/agi-super-team/<skill>/SKILL.md` 相对根为 3 层，在文档界定的范围内。`[官方]`
两点注意事项：① 技能暴露名取自 `SKILL.md` frontmatter 的 `name`（缺失才回退目录名），**不是**目录路径；② 官方在 `OPENCLAW_STATE_DIR` 非默认时会**排除** home 作用域的 `~/.agents/skills`，但 state 自有的托管技能仍正常加载。

> ⚠️ **`<当前配置目录>` 与官方托管技能根存在口径差（`[推定]`，未实测）**：官方把托管技能根挂在 **state 目录**（`~/.openclaw/skills`）。而安装器的 `configDir` 解析是「显式 state 优先 → 否则 `dirname(OPENCLAW_CONFIG_PATH)` → 否则默认 state」（见 `bin/installer/harness-roots.mjs`）。**仅设置 `OPENCLAW_CONFIG_PATH` 且其目录不在 state 目录内时**，安装器会写到 `dirname(configPath)/skills`，而 OpenClaw 按 state 目录找托管技能——两者可能不重合。`OPENCLAW_STATE_DIR` 与 `OPENCLAW_CONFIG_PATH` 同时显式设置的场景下二者一致，无此问题。

**`<当前配置目录>/agency-agents/…` —— 无官方依据。** 官方文档中**不存在 `agency-agents` 这个根**；官方 agent 目录是 `~/.openclaw/agents/<agentId>/agent`（`agentDir`），workspace 默认 `~/.openclaw/workspace`。`agency-agents/` 是**本仓库安装器自订的落盘约定**，它的生效方式是：`--connect` 把每个 `ast-*` 的 `agents.list[].workspace` 指向 `configDir/agency-agents/agi-super-team/<id>`，从而借由 OpenClaw 官方的 **per-agent `workspace`** 机制被读取（官方：`agents.entries.*.workspace`）。`[推定]`（依据 `bin/adapters/openclaw.mjs` 的 `workspace: resolve(targetConfigDir, input.roots.workspaceRoot, id)` + 官方 workspace 语义）
`[实测]`：本机 `~/.openclaw/agency-agents/agi-super-team/ast-ceo/` 确实含 `IDENTITY.md` / `SOUL.md` / `AGENTS.md` / `USER.md` / `TOOLS.md` / `MEMORY.md`——正是官方 workspace bootstrap 文件集，与该推论一致。

> 因此原文「Agent 产物」一行的 `[官方]` 应读作：**路径本身是安装器约定（`[推定]`），但其可被 OpenClaw 识别的机制（per-agent workspace）是 `[官方]`**。

### 配置目录解析顺序

显式 state → 显式配置文件所在目录 → 默认 state。

`--home` 表示 OS Home 基准，**不会静默覆盖** `OPENCLAW_HOME` / `OPENCLAW_STATE_DIR` / `OPENCLAW_CONFIG_PATH`。两者显式冲突时安装器在 Preview 阶段失败且不写文件。

### 已知拒绝条件

`--connect` 会在以下情况拒绝执行：

- `config get` 返回 `__OPENCLAW_REDACTED__`（无法安全整组回写）`[官方]`
  > 佐证：`openclaw config get` 读的是**脱敏后的 config 快照**（secrets 永不打印），`__OPENCLAW_REDACTED__` 是官方保留的脱敏哨兵值，被明确禁止作为字面配置数据提交。整个值都被脱敏时无法安全回写，拒绝是正确行为。
- 主配置含 `$include`（可能修改未纳入事务快照的文件）`[推定]`
  > 官方确认 `$include` 存在且默认可解析范围**仅限配置目录**（`OPENCLAW_INCLUDE_ROOTS` 可放宽）。「含 `$include` 则拒绝」是**本安装器的保守策略**，非 OpenClaw 的限制——官方 `plugins install` 在配置由单文件 `$include` 承载时**会写穿**到拥有该改动的最深层 include 文件，并在多种复杂 include 形态下 fail-closed。安装器选择整类拒绝，是更保守的取舍。

### 版本要求

OpenClaw CLI 要求 Node.js `>=22.22.3 <23`、`>=24.15.0 <25` 或 `>=25.9.0`。AGI Super Team 自身仍支持 Node 18+，该约束仅在调用 OpenClaw CLI 时适用。`[官方]`

官方《Node.js》页补充：**Node 26 是默认且推荐的运行时**（`>=25.9.0` 的包含项），安装脚本在缺 Node 时会自动装；**Node 23 明确不支持**。因此更准确的表述是「`>=22.22.3 <23` 或 `>=24.15.0`（不含 24.14.x 及更早）或 `>=25.9.0`（含 Node 26）」。

本机实测版本：OpenClaw 2026.6.8 (844f405) `[实测]`。

## 兼容 bundle 与自动探测（决定集中化包形态的关键事实）

**自动探测是官方行为，已被证实。** OpenClaw 可安装四类外部生态的 bundle：中立的 **Agent Plugins** 标准，以及 **Codex / Claude / Cursor**。官方《Plugin bundles》原文：「Instead of requiring authors to rewrite them as native OpenClaw plugins, OpenClaw detects these formats and maps their supported content into the native feature set.」`[官方]`

### 官方自动探测的判定顺序

1. `openclaw.plugin.json`，或含 `openclaw.extensions` 的合法 `package.json` → **原生 OpenClaw 插件**
2. 客户端专属标记 `.codex-plugin/` / `.cursor-plugin/` / `.claude-plugin/` → **该格式的 bundle**
3. 根部 `plugin.json` → **Agent Plugins bundle**（须含 Agent Plugins 标准的 `$schema`）
4. **无清单的默认 Claude 布局**（`skills/`、`commands/`、`agents/`、`hooks/`、`.mcp.json`、`.lsp.json`、`settings.json`）→ **Claude bundle**

同一包同时带客户端专属标记与根部 `plugin.json` 时，客户端专属格式胜出；同时带原生清单与 bundle 标记时，走原生路径（防止双格式包被部分安装）。

### bundle 各能力的实际映射（**决定能不能替代适配器的关键**）

**已被 OpenClaw 真正执行的能力** `[官方]`：

| 能力 | 映射方式 | 适用格式 |
|---|---|---|
| Skill 内容 | bundle 的技能根按普通 OpenClaw 技能加载 | 全部格式 |
| 命令 | `commands/`（Claude）与 `.cursor/commands/` 当作**技能根** | Claude、Cursor |
| MCP 工具 | bundle 的 MCP 配置并入内嵌 OpenClaw 设置 | 全部格式 |
| Hook 包 | 仅限 OpenClaw 风格的 `HOOK.md` + `handler.ts` 布局 | 主要是 Codex |
| LSP | Claude `.lsp.json` | Claude |
| 设置 | Claude `settings.json` 导入为内嵌默认值 | Claude |

**仅被识别、不会执行的能力** `[官方]` —— 原文明确列出：

- Claude 的 **`agents`**、`hooks/hooks.json` 自动化、`outputStyles`
- Cursor 的 `.cursor/agents`、`.cursor/hooks.json`、`.cursor/rules`
- Codex 的 `.app.json` 元数据（超出能力上报部分）

> ### 结论（回答「集中化包要不要为 OpenClaw 单独做格式」）
>
> **自动探测能覆盖的只有技能与 MCP 工具；它覆盖不到 agent 角色编排。**
>
> OpenClaw 对 Claude bundle 的 `agents/` 目录是 **detect-only（只识别、不执行）**。也就是说，本项目 `agents/` 定义的 14 个 canonical 角色与 92 个专家，即使把仓库根目录**原样**作为 Claude bundle 安装进 OpenClaw，也**不会**变成可调用的 OpenClaw agent。
>
> 实测旁证：本仓库根**已经**存在 `.claude-plugin/plugin.json`（`skills: "./skills"`）——已经是形态完整的 Claude bundle，且其 `skills/` 可被 OpenClaw 直接吃下。但它**无法**替代 `bin/adapters/openclaw.mjs` 的工作，因为后者真正做的是：把每个角色渲染成 OpenClaw **workspace bootstrap 文件集**，再把 `agents.list` 逐条 upsert（含 `ast-*` 前缀的托管边界、`allowAgents` 委派白名单、`requireAgentId`、叶子 `tools.deny: ["sessions_spawn"]`）——这些都不在任何 bundle 映射表内。
>
> **因此：集中化包若要把角色**编排**能力带进 OpenClaw，仍需保留一个 OpenClaw 专用产物路径（workspace 文件 + `agents.list` 合并）；只有技能分发可以走 bundle 自动探测省下来。** 二者可并存：技能走 bundle（零适配），agent 编排走适配器。
>
> 若未来想改走原生插件形态，则必须新写 `openclaw.plugin.json`——官方对原生插件的要求（`id` + 内联 `configSchema`）本仓库尚未满足。

## 未做的事

本仓库**未**把 AGI Super Team 封装为原生 OpenClaw **插件**（无 `openclaw.plugin.json`，`package.json` 也无 `openclaw` 字段——`[实测]` 两者均确认缺失）。当前只走安装器的文件落盘 + 配置合并路径。

> 注意「未做成插件」**不等于**「未做成 bundle」：仓库根已有 `.claude-plugin/plugin.json`，形态上是合法 Claude bundle，只是其中的 `agents/` 对 OpenClaw 属 detect-only（见上节）。

## 相关文档

- [装配机制总览](./README.md)
- [harness-adapters.md](../guides/harness-adapters.md) — 版本化路径依据
- [OpenClaw — Plugins CLI](https://docs.openclaw.ai/cli/plugins)
- [OpenClaw — Install plugins](https://docs.openclaw.ai/cli/plugins/install) — 源 locator 与选源规则
- [OpenClaw — Plugin manifest](https://docs.openclaw.ai/plugins/manifest)
- [OpenClaw — Plugin bundles](https://docs.openclaw.ai/plugins/bundles) — 自动探测顺序与能力映射
- [OpenClaw — Environment variables](https://docs.openclaw.ai/help/environment)
- [OpenClaw — Skills](https://docs.openclaw.ai/tools/skills)
- [OpenClaw — Multi-agent routing](https://docs.openclaw.ai/concepts/multi-agent)
- [OpenClaw — Node.js 版本要求](https://docs.openclaw.ai/install/node)
