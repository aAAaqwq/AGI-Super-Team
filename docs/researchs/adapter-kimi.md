# Kimi 装配

> **状态**：`[部分核实]` —— 机制层已比对**官方文档原文**核实（2026-09 复核轮，本机仍未安装 `kimi` CLI，`which kimi` 为空，故**无任何 `[实测]` 证据**）。已核实项见下表「证据」列；已修正项见 [核实记录](#核实记录)。**客户端加载行为仍未实测**，在实测确认前不得声称本仓库在 Kimi 上可用。

> **⚠️ 两个产品的文档被混用了**（本轮最重要发现）：Kimi 有两条产品线，官方文档站与仓库各自维护，**技能/插件路径并不一致**：
>
> | 产品 | 文档站 | 仓库 | 状态 |
> |---|---|---|---|
> | **Kimi Code CLI**（TypeScript，`0.x`） | `kimi.com/code/docs` | `MoonshotAI/kimi-code` | **当前主线** |
> | kimi-cli（Python，`1.4x`） | `moonshotai.github.io/kimi-cli` | `MoonshotAI/kimi-cli` | 官方 README 声明**逐步下线**（"will be gradually wound down"） |
>
> 本文档此前引用的 `kimi plugin` shell 子命令与 `~/.kimi/plugins/` 均出自 **legacy Python 版**；当前 Kimi Code 的对应机制不同（见下）。参考实例：[obra/superpowers 的 Kimi 接入](https://github.com/obra/superpowers/blob/main/docs/README.kimi.md) 用的是 `.kimi-plugin/plugin.json`。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| manifest 位置 1 | `.kimi-plugin/plugin.json` | `[官方]` ✅ 已核实 |
| manifest 位置 2 | `kimi.plugin.json`（**优先级更高**） | `[官方]` ✅ 已核实 |
| 两者同时存在 | 以 `kimi.plugin.json` 为准 | `[官方]` ✅ 已核实（原文逐字："When both files exist, `kimi.plugin.json` takes precedence."） |
| 插件管理（当前 Kimi Code） | TUI 斜杠命令 `/plugins`（`list`/`install`/`info`/`enable`/`disable`/`remove`/`reload`/`marketplace`/`mcp enable\|disable`） | `[官方]` ⚠️ **已修正**（原文写 `kimi plugin` 命令） |
| 插件管理（legacy kimi-cli） | shell 子命令 `kimi plugin install\|list\|info\|remove` | `[官方]` ⚠️ 仅 legacy Python 版有 |
| 插件安装位置（当前 Kimi Code） | 托管副本 `$KIMI_CODE_HOME/plugins/managed/<id>/`，安装记录 `$KIMI_CODE_HOME/plugins/installed.json` | `[官方]` ⚠️ **已修正** |
| 插件安装位置（legacy kimi-cli） | `~/.kimi/plugins/<plugin>/` | `[官方]` ⚠️ 仅 legacy Python 版 |
| 数据根 | `$KIMI_CODE_HOME`（默认 `~/.kimi-code`） | `[官方]` ✅ 已核实 |

### 本仓库只有 `.kimi-plugin/plugin.json` 够不够？

**够，且不需要补 `kimi.plugin.json`。** 这是本轮的可操作结论，依据有两条彼此独立：

1. **优先级问题不存在**：「两者同时存在时以 `kimi.plugin.json` 为准」这条规则**只在两个文件都存在时才生效**。本仓库只有 `.kimi-plugin/plugin.json`，不构成冲突，官方把它列为**并列的合法位置之一**（"Manifest 可以放在以下任一位置"）。
2. **不必迁移的理由**：`kimi.plugin.json` 的优先级优势**只影响「同名时读哪一个」**，而按上面的结论，Kimi **根本不会自动读取工作目录里的任一 manifest**——两者都要经 `/plugins install` 才会被消费。既然自动生效这条路径不存在，换成优先级更高的文件名**不会带来任何行为差异**。

> **反过来说**：如果哪天想同时兼容别的生态（某些工具约定根级 `*.plugin.json`），补一个 `kimi.plugin.json` 是无害的；但**在当前机制下它不会让插件「更容易被加载」**。维持现状是正确选择。

### 本仓库已有的 manifest

`.kimi-plugin/plugin.json` **正是 Kimi 的官方合法位置之一**，不是自造（`[官方]`，已核实）：

```json
{
  "name": "agi-super-team",
  "version": "1.6.0",
  "description": "...",
  "author": { "name": "Daniel Li", "url": "..." },
  "skills": "./skills"
}
```

**manifest 已核实字段**（逐字段比对官方「支持的字段」表）：

| 本仓库字段 | 官方是否支持 | 备注 |
|---|---|---|
| `name` | ✅ 必填 | 须匹配 `[a-z0-9][a-z0-9_-]{0,63}` —— `agi-super-team` 通过 |
| `version` / `description` / `author` | ✅ 展示元数据 | 官方列为纯展示字段 |
| `skills: "./skills"` | ✅ | 官方要求为 plugin 根目录内的 `./` 路径；仓库根 `skills/` 存在且含 **837 个 `SKILL.md`**（`find skills -name SKILL.md \| wc -l`，`[实测]` 本机） |

**未声明但官方支持的字段**（本仓库暂未使用，供后续扩展参考）：`agents`、`commands`、`sessionStart.skill`、`skillInstructions`、`systemPrompt` / `systemPromptPath`、`mcpServers`、`interface`、`keywords` / `homepage` / `license`。

> **关键不确定性（2026-09 复核已找到官方依据，结论：不会自动生效）**：上一轮把「仓库放 manifest 是否自动生效」列为未找到依据。本轮在官方 Plugins 页的**注意事项**中找到了直接答案——
>
> > "Plugin 目前按用户安装，对所有项目生效，**暂不支持项目级安装范围**。"
> > —— <https://www.kimi.com/code/docs/kimi-code-cli/customization/plugins.html>
>
> 同页另一条同样封死了「编辑源目录即生效」的路径：
>
> > "本地安装会被拷贝到 `$KIMI_CODE_HOME/plugins/managed/<id>/`，CLI 始终从这份托管副本运行。**安装后编辑原始源目录不会生效，需重新安装。**"
>
> **两条合起来 = 仓库里放 manifest 绝不会被自动读取**：既没有「项目级作用域」（所以工作目录里的 `.kimi-plugin/` 不在任何自动扫描路径上），安装后运行的又是托管副本（所以改仓库也不影响已装插件）。因此本仓库的 manifest **只能视为「可被 `/plugins install` 消费的插件源」，不是自动生效的注册**——级别从 `[推定]` 升为 `[官方]`（否定式结论）。
>
> 这也解释了为什么生态项目 [verona-dev-plugin 的 INSTALL.md](https://github.com/burnt-labs/verona-dev-plugin/blob/main/INSTALL.md) 对 Kimi 只写"用 TUI `/plugins install`（URL 或路径）"而没有自动发现一说。

## 技能

| 项目 | 值 | 证据 |
|---|---|---|
| 技能格式 | `SKILL.md`（YAML frontmatter + Markdown 正文） | `[官方]` ✅ 已核实 |
| 用户级技能 | `$KIMI_CODE_HOME/skills/`（默认 `~/.kimi-code/skills/`）、`~/.agents/skills/` | `[官方]` ✅ 已核实 |
| 项目级技能 | `.kimi-code/skills/`、`.agents/skills/` | `[官方]` ✅ **已升级**（原文标 `[社区]`） |
| 额外目录 | `extra_skill_dirs`（config.toml 顶层）或 `--skills-dir` | `[官方]` ✅ 已核实 |
| 优先级 | Project > User > Extra > Built-in | `[官方]` ✅ 已核实（原文逐字一致） |
| `SKILL.md` 必填字段 | 目录型 skill 的 `name` 与 `description` **均为必填**，缺任一即解析失败 | `[官方]` |

**关键点**：`~/.agents/skills/` **确实被 Kimi 读取** `[官方]`，因此一次 Codex 安装写入的技能理论上可被 Kimi 识别 —— 这一点成立。但注意粒度：

- 官方原文称其为 "generic cross-tool Skills" 通用目录，**并未**称它与 Claude Code 共享同一 skill 根；共享关系针对的是 **brand group**（`~/.kimi/skills/` → `~/.claude/skills/` → `~/.codex/skills/`，**三者互斥取第一个存在者**），而 `~/.agents/skills/` 属于独立的 generic group，两组结果**独立合并**。
- **`~/.claude/skills/` 的兼容行为出自 legacy kimi-cli 文档**（且是同组互斥，不是并列叠加）。当前 Kimi Code 文档的 user 级只列 `$KIMI_CODE_HOME/skills/` 与 `~/.agents/skills/`，**未见** `~/.claude/skills/`。→ 原文「与 Claude Code 共享同一 skill 根」应降为 `[推定]`。

### 路径不受 `KIMI_SHARE_DIR` 影响

`[官方]` ✅ 已核实，原文逐字为 "Skills paths are independent of `KIMI_SHARE_DIR`"（legacy 文档），当前 Kimi Code 文档亦一致：`~/.agents/skills/` 留在真实 OS home 下以便跨工具共享，只有 `$KIMI_CODE_HOME/skills/` 随数据根移动。自定义技能路径用 `--skills-dir` 或 `extra_skill_dirs`。

### 插件自带技能

插件可通过 manifest 的 `skills` 字段（一个或多个 `./` 路径，须位于 plugin 根目录内）提供技能；省略 `skills` 时，根目录下的单个 `SKILL.md` 被当作一个 skill root。插件技能与普通 Agent Skills **格式相同** `[官方]`。

## Agent 机制

- 插件可携带 `agents/` 目录，或通过 manifest 的 `agents` 字段声明 `./` 路径（可多个目录） `[官方]` ✅ 已核实
- Agent 文件格式与 Kimi 的自定义 Agent 相同（**Markdown**，frontmatter 声明 name/description/tool permissions，正文为 system prompt） `[官方]` ✅ 已核实
- 插件 Agent 的优先级**低于**其他文件来源：同名时用户级、额外目录、项目级与 `--agent-file` 都会覆盖 `[官方]` ✅ 已核实
- 覆盖内置 Agent 需在 frontmatter 显式写 `override: true` `[官方]` ✅ 已核实
- 安装/启用/禁用/移除插件后，Agent 列表在新会话或 `/reload` 时刷新（v2 引擎当前会话还支持 `/plugins reload`） `[官方]` ✅ 已核实
- 插件可声明 `mcpServers` 复用 MCP schema，默认启用、可从 `/plugins` 中禁用 `[官方]` ✅ 已核实

## 未验证的部分

本机无 `kimi` CLI（`which kimi` 空，`[实测]`），以下**均无实测证据**。官方文档已能解释机制，但无法证明本仓库的产物被正确加载：

1. ~~Kimi 是否**自动读取**工作目录下的 `.kimi-plugin/plugin.json`~~ —— **本轮已由官方文档否证**：官方明示「暂不支持项目级安装范围」+「CLI 始终从托管副本运行，编辑源目录不生效」，故不存在自动读取。**该问题已关闭**（结论为否定），只剩「安装流程本身是否跑通」待实测。
2. `skills: "./skills"` 是否指向本仓库 857 个 `SKILL.md` 的根目录并按预期发现
3. `~/.agents/skills/` 中的技能是否被 Kimi 的 Agent Skills 系统识别（文档层面 `[官方]` 已确认读取该路径，但端到端未实测）
4. Kimi 的 agent 加载是否与 **Claude Code 的** Markdown frontmatter 完全兼容 —— 官方只说与「Kimi 自定义 Agent 格式相同」，**未承诺与 Claude Code 格式兼容**
5. `name: "agi-super-team"` 的插件在 `/plugins info` 下的 diagnostics 是否干净

## 待办

- [ ] 安装 Kimi Code CLI（`curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash`，或 `npm install -g @moonshot-ai/kimi-code`），实测 `/plugins install <仓库根>` 是否识别本仓库
- [ ] 实测后把本文档「未验证的部分」逐条勾掉，并把状态改为 `[实测]` 并记录输出
- [ ] 核实是否为该 manifest 补 `version` 之外的 `interface` / `sessionStart.skill` 字段以对齐官方推荐形态

## 核实记录

本轮（2026-09）用 tavily 检索官方文档 + 官方仓库核实，发现并修正如下：

| 原结论 | 核实结果 | 处置 |
|---|---|---|
| 状态标 `[未验证]` | 机制层可核实的部分已全部核实，但**客户端行为仍无实测**（本机无 CLI） | 改为 `[部分核实]`，明确无 `[实测]` 证据 |
| `kimi plugin` 命令管理插件 `[官方]` | **已修正**：该 shell 子命令属 **legacy Python `kimi-cli`**（其文档站 `moonshotai.github.io/kimi-cli`，仓库 README 声明逐步下线）。当前 **Kimi Code** 的插件管理是 TUI 斜杠命令 `/plugins`；非交互 shell 子命令 `kimi plugins ...` 到 2026-07 仍是 [未实现的 feature request #1399](https://github.com/MoonshotAI/kimi-code/issues/1399) | 表中拆成两行并注明归属产品 |
| 插件安装位置 `~/.kimi/plugins/<plugin>/` `[官方]` | **已修正**：该路径属 legacy Python 版。当前 Kimi Code 为 `$KIMI_CODE_HOME/plugins/managed/<id>/` + `installed.json` | 表中拆成两行 |
| 项目级技能标 `[社区]` | **已升级为 `[官方]`**：当前文档逐字列出 `.kimi-code/skills/` 与 `.agents/skills/` | 证据等级提升 |
| 「Kimi 文档亦称该路径与 Claude Code 共享同一 skill 根」 | **降级为 `[推定]`**：该兼容行为（`~/.claude/skills/`）出自 legacy 文档且是 brand group **互斥**（取第一个存在者），非并列；当前 Kimi Code 文档 user 级**未列** `~/.claude/skills/` | 加注说明，避免误导 |
| `SKILL.md`「与 Agent Skills 开放标准一致」 | 已核实为真（官方明确 SKILL.md + YAML frontmatter，插件技能与普通 Agent Skills 同格式），但官方术语是 "Agent Skills" 且**未提及 agentskills.io** | 保留结论，去掉未经官方确认的标准署名 |
| manifest 位置与优先级 | **完全属实**，官方原文逐字："When both files exist, `kimi.plugin.json` takes precedence." | 标注 ✅ 已核实 + 引原文 |
| 「仓库放 manifest 是否自动生效」`[推定]` | **本轮升级为 `[官方]`（否定式）**：官方注意事项明示「Plugin 目前按用户安装，对所有项目生效，**暂不支持项目级安装范围**」+「本地安装会被拷贝到 `$KIMI_CODE_HOME/plugins/managed/`，CLI 始终从这份托管副本运行；安装后编辑原始源目录不会生效」 | 关掉该开放项，结论=**不会自动生效** |
| 「只有 `.kimi-plugin/plugin.json` 是否够」 | **够**。优先级规则仅在两文件并存时生效；且既不自动生效，补 `kimi.plugin.json` 无行为差异 | 新增可操作结论小节 |
| 数据根 `$KIMI_CODE_HOME`（默认 `~/.kimi-code`） | **完全属实**，官方数据位置页列出完整目录树 | 标注 ✅ 已核实 |

**检索关键词与结果**（未能找到依据的方向已如实记录）：

- ✅ 命中：`Kimi Code CLI plugins custom plugin manifest kimi.plugin.json .kimi-plugin/plugin.json`、`Kimi Code CLI skills directory ~/.agents/skills SKILL.md`、`"kimi plugin" command list install enable disable remove subcommands`、`install Kimi Code CLI npm package name`
- ❌ 无结果：检索「Kimi Code 仓库内 `/kimi.plugin.json` 自动发现/免安装加载」这一类关键词，官方文档与第三方生态项目说明**都只描述 `/plugins install` 安装流程**，未找到「工作目录 manifest 自动生效」的任何官方依据 → 维持 `[无法证实]`

## 相关文档

- [装配机制总览](./README.md)
- [Kimi Code — Plugins](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html)（当前产品，本页多数结论出自此页）
- [Kimi Code — Agent Skills](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html)
- [Kimi Code — Data locations](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/data-locations.html)
- [kimi-cli — Plugins (Beta)](https://moonshotai.github.io/kimi-cli/en/customization/plugins.html)（**legacy Python 版**，`kimi plugin` 子命令与 `~/.kimi/plugins/` 出自此页）
- [kimi-cli — Agent Skills](https://moonshotai.github.io/kimi-cli/en/customization/skills.html)（**legacy Python 版**，`~/.claude/skills/` 兼容出自此页）
- [MoonshotAI/kimi-code #1399 — 非交互 `kimi plugins` CLI](https://github.com/MoonshotAI/kimi-code/issues/1399)（说明当前无 shell 插件管理命令）
