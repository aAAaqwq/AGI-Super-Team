# DeepSeek Harness (DSH) 装配

> **状态**：**本仓库当前不支持 DSH**。本文记录 DSH 的实际机制与接入障碍，供评估使用。

## 机制

DSH 是 DeepSeek 的 agent runtime / harness 层，架构原则是「**everything is a plugin**」，基于 Cordis 内核。`[官方]`

| 项目 | 值 | 证据 |
|---|---|---|
| 插件安装 | `dsh plugin --profile <profile> add "github:owner/repo#main"` | `[官方]` |
| 启动 | `npx @deepseek-ai/dsh web` | `[官方]` |
| 生态主题 | 插件仓库建议带 `#dsh` GitHub topic 以便索引 | `[社区]` |
| 插件形态 | TypeScript 模块，通过 `apply(ctx)` 注册，卸载自动清理 | `[官方]` |

### 技能根（按 rank，数字越小优先级越高）

| Rank | 路径 | 作用域 |
|---|---|---|
| 100 | `<项目根>/.dsh/skills` | 项目 |
| 200 | `<项目根>/.agents/skills` | 项目 |
| 300 | `Config.customSkillDirs` | 自定义 |
| 400 | `~/.dsh/skills`（`$DSH_HOME`） | 用户 |
| 500 | `~/.agents/skills` | 用户 |

`[官方]`

### 技能格式

- `<name>/SKILL.md` 或平铺 `<name>.md` `[官方]`
- **只扫一层，不递归**——埋到二级子目录不会被发现 `[官方]`
- frontmatter 必需 `name`（kebab-case）+ `description`；非法则**静默丢弃**（fail-closed）`[官方]`
- 目录型技能（含 `references/`、`scripts/`）必须声明 `resourceBase`，否则相对路径断裂 `[社区]`

### 环境变量

`DSH_HOME`（默认 `~/.dsh`）、`DSH_AGENTS_HOME`（默认 `~/.agents`）`[官方]`

## Agent 机制 —— 接入 DSH 的主要难点

**DSH 没有独立于 Skill 的 agent 文件目录。** 角色与指令通过 **AGENTS.md 指令链**注入。`[官方]`

| 项目 | 值 |
|---|---|
| 指令文件候选 | `AGENTS.md`、`CLAUDE.md` |
| 本地覆盖 | `AGENTS.local.md`、`CLAUDE.local.md` |
| 项目根标记 | `['.git']` |
| 用户全局 | `$DSH_HOME/AGENTS.md`（默认 `~/.dsh/AGENTS.md`） |
| 加载顺序 | 项目根 → 会话工作目录，**宽 → 专** |
| 渲染预算 | `maxBytes` 必需（典型部署 65536 字节）；单文件 `maxSourceBytes` 默认 1 MiB |

去重规则：trim 后内容相同的同级文件只渲染一次（例如 `CLAUDE.md` 与 `AGENTS.md` 重复时不会重复注入）。

**Subagent** 由 `tool-subagent` 插件提供，是**插件能力而非文件约定**。`[官方]`

### 为什么这构成障碍

现有四个 primary harness（Claude Code / Codex / OpenClaw / Hermes）的 Adapter 都按「**每个角色一个原生文件**」建模——Claude 写 `ast-ceo.md`、Codex 写 `ast-ceo.toml`。

DSH **不适用这个模型**：它没有 agent 文件目录，角色只能作为 `AGENTS.md` 指令链的一部分注入。这意味着接入 DSH 需要一条**与现有四个 Adapter 不同的产物渲染路径**。

## 接入 DSH 需要的改动

详见 [DSH primary adapter 实施计划](../plans/dsh-primary-adapter.md)。摘要：

1. 新增 CLI 目标 → 同时改三处「恰好 18 个」硬约束
2. 实现 `bin/adapters/dsh.mjs`，导出 `ADAPTER_ID` / `renderAdapterArtifacts` / `buildConnectionSpec`
3. 加入 `priorityHarnesses`（硬编码于 `bin/installer/catalog.mjs`）
4. 解决 agent 装配模型差异（最主要工作量）

## 可以低成本拿到的部分

DSH 的 rank 500 技能根是 `~/.agents/skills/`，**与 Codex 的落盘位置相同**（实测 Codex 安装写入 170 个技能）。

所以**技能层**其实已经可用——用户跑一次 `--tool codex --install`，DSH 就能读到这些技能。缺的是 **agent 层**与**官方接入路径**。

但注意：这是**行为巧合**，不是本仓库的 DSH 支持声明。DSH 的客户端行为**未实测**（本机未安装 `dsh`）。

## 待办

- [ ] 安装 DSH，实测其是否读取 `~/.agents/skills/`
- [ ] 评估 `resourceBase` 对目录型技能的要求（本仓库技能多含 `references/`、`scripts/`）
- [ ] 按实施计划评估投入产出

## 相关文档

- [装配机制总览](./README.md)
- [DSH primary adapter 实施计划](../plans/dsh-primary-adapter.md)
- [DeepSeek Harness — Skill System](https://deepseekdocs.com/en/docs/features/skills)
