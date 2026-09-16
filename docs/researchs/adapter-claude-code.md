# Claude Code 装配

> **核实记录（2026-09-16）**：本文每条机制结论已对照 Claude Code 官方文档逐条核实，并附本机实测。
> 证据等级：`[官方]`（附 URL）/ `[实测]`（附命令+输出）/ `[推定]` / `[无法证实]`。
> 实测环境：**Claude Code v2.1.207**（`claude --version`）。凡标「v2.1.2xx+」的特性，在本机版本上**未生效**。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| marketplace 位置 | 本地目录被 `plugin marketplace add` 时**必须**在仓库根 `.claude-plugin/marketplace.json` | `[官方]` + `[实测]` |
| 校验 | `claude plugin validate <path>`，`--strict` 存在（警告当错误、exit 1） | `[官方]` + `[实测]` |
| 插件本体位置 | **不能**靠 `metadata.pluginRoot` 收拢；`source: "./plugins/<name>"` 逐个显式写 | `[官方]` + `[实测]` |
| 技能根 | `~/.claude/skills/<name>/SKILL.md`（个人级；另有项目/企业/嵌套等根） | `[官方]` |
| Agent 格式 | Markdown + YAML frontmatter | `[官方]` |
| 单 marketplace 多插件 | **支持**，`plugins[]` 可含任意多个 entry，`source` 可指向不同子目录 | `[官方]` + `[实测]` |

### 目录名：本地目录源是硬要求

对**本地目录**调用 `claude plugin marketplace add <dir>` 时，Claude Code 只认
`<dir>/.claude-plugin/marketplace.json`：

```
$ claude plugin marketplace add /tmp/mkt2      # marketplace.json 放在目录根，不在 .claude-plugin/
Adding marketplace…✘ Failed to add marketplace: Marketplace file not found at /tmp/mkt2/.claude-plugin/marketplace.json
```

官方把 `.claude-plugin/marketplace.json` 描述为「in your repository root」这一**约定位置**
（[marketplace 文档](https://code.claude.com/docs/en/plugin-marketplaces)，"Create the marketplace file" 一节），
本地目录源没有参数可改这个相对路径。**结论维持**：改名即放弃 Claude Code 支持。

> 边界（`[官方]`）：官方对 v2.1.196+ 说明了一处**非** `.claude-plugin/` 的容忍——校验器会把
> `marketplace.json` 放在仓库根时「按该文件自身所在目录解析 source」并逐条检查。这**只影响
> `plugin validate` 的校验路径**，不改变 `marketplace add` 的发现规则。见下文「校验」小节。

`plugin validate` 命中的错误文案与本仓库原记录一致（`[官方]` 错误表）：

```
No manifest found in directory. Expected .claude-plugin/marketplace.json or .claude-plugin/plugin.json
```

### `source` 路径解析规则

- 相对 **marketplace 根**解析（即含 `.claude-plugin/` 的目录），**不是**相对 `.claude-plugin/` 本身
- **不允许 `../`**：校验器直接报 `plugins[N].source: Path contains ".."`；运行时则是
  `path escapes plugin directory`（组件路径同样受限）
- 含 `/` 的路径**必须**以 `./` 开头，如 `"./plugins/demo"`
- 官方原话（[plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces#relative-paths)）：
  > Paths resolve relative to the marketplace root, which is the directory containing `.claude-plugin/`. …
  > Don't use `../` to reference paths outside the marketplace root.

**以上三条经实测确认**（含 `./plugins/demo` 与 `"./"` 两种形态）。

### `metadata.pluginRoot`：存在，但语义被原记录误解（**已修正**）

原记录称「通过 `metadata.pluginRoot`（v2.1.239+）可收拢到 `plugins/`」并称之为「官方途径」。
核实结论：**该字段确实存在，但只能改写「裸名 source 的解析基准」，不会移动、也不会识别插件本体位置。**
它不减少任何路径书写，因此**不是**收拢插件本体的途径。

官方定义（[plugin-marketplaces → Optional fields / Relative paths](https://code.claude.com/docs/en/plugin-marketplaces#relative-paths)）：

> `metadata.pluginRoot` | string | Directory that Claude Code resolves **bare** plugin source names under. …
> Requires Claude Code v2.1.239 or later.
>
> A **bare name** is a single directory name with no `/`, such as `"formatter"`. … With
> `"pluginRoot": "./plugins"`, Claude Code resolves `"source": "formatter"` to `./plugins/formatter`.
> … Claude Code ignores it for a source that already starts with `./`. A source that contains a `/`,
> such as `team-a/formatter`, isn't a bare name and still needs the `./` prefix, even when
> `metadata.pluginRoot` is set.

即：`pluginRoot` 只在 `source` 是**裸目录名**（无 `/`、无 `./` 前缀）时参与解析。
`source: "./plugins/formatter"` 这类显式路径**完全绕过**它；`source: "a/b"` 也**不是**裸名，仍要写 `./`。

**本机实测（v2.1.207，`[实测]`）**——与另一 agent 的实测结论一致：

| # | marketplace 配置 | `claude plugin validate` 结果 |
|---|---|---|
| C | 裸名 `"source": "demo"`，**无** `pluginRoot` | `✘ plugins.0.source: Invalid input` |
| D | 顶层 `pluginRoot`（非 `metadata` 下）+ 裸名 | `✘ plugins.0.source: Invalid input` |
| E | `metadata.pluginRoot: "./plugins"` + `"source": "./demo"` | `✔ Validation passed with warnings` |
| — | `metadata.pluginRoot: "./plugins"` + 裸名 `"source": "demo"` | `✘ plugins.0.source: Invalid input` |

```bash
$ cd /tmp/plugroot-test && claude plugin validate .
Validating marketplace manifest: …/.claude-plugin/marketplace.json
✘ Found 1 error:
  ❯ plugins.0.source: Invalid input
✘ Validation failed
```

安装路径同样被拒（`[实测]`）：

```bash
$ claude plugin marketplace add /tmp/mkt3     # 用 metadata.pluginRoot + 5 个裸名
✔ Successfully added marketplace: mkt3 (declared in user settings)
$ claude plugin install codex@mkt3
Installing plugin "codex@mkt3"...✘ Failed to install plugin "codex@mkt3":
  This plugin uses a source type your Claude Code version does not support. Update Claude Code and try again.
```

> 注意：`marketplace add` **成功**、`validate` **失败**、`install` **失败**——三者结论不一致，
> 只看 `marketplace add` 会误判为可用。这是原记录踩坑的直接原因。

**修正后的结论**：把插件本体收拢到 `plugins/` 的可行做法是
**在 marketplace 条目里逐个写显式相对仓库根的路径**：

```json
{ "name": "codex", "source": "./plugins/codex" }
```

`metadata.pluginRoot` 仅在「愿意为每个条目写裸名 + 全队 Claude Code ≥ v2.1.239」时有简写价值，
且官方对**组织同步**另有拒绝规则（`[官方]`）：

> If you list a plugin by bare name under `metadata.pluginRoot`, organization sync rejects it as an
> unsupported source, so write the path out, such as `./plugins/deploy-tools`.

即走 managed-marketplace 同步时，裸名一律不被接受。**建议：不使用 `pluginRoot`。**

### 单 marketplace 多插件（**本项目五包集中化的关键输入**）

原记录未覆盖此点。核实结论：**可行，且这是官方推荐做法。**

官方（[plugin-marketplaces → Required fields](https://code.claude.com/docs/en/plugin-marketplaces#required-fields)）：

> `plugins` | array | List of available plugins
>
> (关于 `name`) **To publish multiple plugins under one marketplace name, list them all in a single
> `marketplace.json`.**

条目侧约束（`[官方]`）：

- `plugins[]` 里每个 entry 至少需要 `name` + `source` 两个字段
- `source` 为相对路径时，**各自独立**相对 marketplace 根解析，因此**可以指向不同子目录**
- `name` 在同一 marketplace 内**必须唯一**（否则 `Duplicate plugin name "x" found in marketplace`）
- 该 marketplace 的名字在同一用户下唯一；重名会**替换**前一个（`Each user can register only one
  marketplace per name`）——所以「一个 marketplace 暴露五个包」天然优于「五个 marketplace」

**本机实测（v2.1.207，`[实测]`）**——五包结构：

```
/tmp/mkt3/
├── .claude-plugin/marketplace.json
└── plugins/{codex,claudecode,openclaw,hermes,deepseek-harness}/
    ├── .claude-plugin/plugin.json
    └── skills/<name>-pack/SKILL.md
```

```json
{
  "name": "mkt4",
  "description": "d",
  "owner": { "name": "t" },
  "plugins": [
    { "name": "codex",            "source": "./plugins/codex" },
    { "name": "claudecode",       "source": "./plugins/claudecode" },
    { "name": "openclaw",         "source": "./plugins/openclaw" },
    { "name": "hermes",           "source": "./plugins/hermes" },
    { "name": "deepseek-harness", "source": "./plugins/deepseek-harness" }
  ]
}
```

```bash
$ claude plugin validate /tmp/mkt3
Validating marketplace manifest: /tmp/mkt3/.claude-plugin/marketplace.json
✔ Validation passed

$ claude plugin marketplace add /tmp/mkt3
Adding marketplace…✔ Successfully added marketplace: mkt4 (declared in user settings)

$ claude plugin install codex@mkt4
Installing plugin "codex@mkt4"...✔ Successfully installed plugin: codex@mkt4 (scope: user)
$ claude plugin install deepseek-harness@mkt4
Installing plugin "deepseek-harness@mkt4"...✔ Successfully installed plugin: deepseek-harness@mkt4 (scope: user)

$ claude plugin list
Installed plugins:
  ❯ codex@mkt4            Version: 1.0.0  Scope: user  Status: ✔ enabled
  ❯ deepseek-harness@mkt4 Version: 1.0.0  Scope: user  Status: ✔ enabled
```

**结论：一个 marketplace 同时暴露五个包完全可行**，每个 entry 的 `source` 指向不同子目录，
五个包可独立安装/独立启用。无需五个 marketplace，也无必要使用 `pluginRoot`。
（实测装了两个包后已卸载并移除测试 marketplace，未污染本机配置。）

## 校验

```bash
claude plugin validate <path> [--strict]
```

`--strict` **存在**（`[官方]` + `[实测]`）：

```bash
$ claude plugin validate --help
Usage: claude plugin validate [options] <path>
Validate a plugin or marketplace manifest
Options:
  -h, --help  Display help for command
  --strict    Treat warnings as errors (exit 1). Use in CI to fail on
              unrecognized fields, missing metadata, and other issues that the
              runtime tolerates.
```

官方描述（[plugins-reference → plugin validate](https://code.claude.com/docs/en/plugins-reference)）：

> `--strict` | Treat warnings as errors and exit 1 on them. Use in CI to catch issues the runtime
> tolerates, such as unrecognized fields
> `--json` | Output the validation report as one JSON object with the same exit codes.
> Requires Claude Code v2.1.259 or later
> Within an interactive session, `/plugin validate <path>` runs the same checks inline.

**本仓库实测（`[实测]`）**：

```bash
$ claude plugin validate .
Validating marketplace manifest: …/AGI-Super-Team-release-1.6.0/.claude-plugin/marketplace.json
✔ Validation passed
```

补 `author` 字段前有 1 个警告：

```
⚠ Found 1 warning:
  ❯ plugins[0] plugin.json → author: No author information provided. Consider adding author details for plugin attribution
```

补齐 `author` 后**零警告通过**。`--strict` 的行为已实测（`[实测]`，v2.1.207）：
同一份缺 `author` 的清单，不加 `--strict` 时 `exit=0`，加 `--strict` 后 `exit=1`：

```
$ claude plugin validate . --strict
⚠ Found 2 warnings:
  ❯ description: No marketplace description provided. …
  ❯ plugins[0] plugin.json → author: No author information provided. …
✘ Validation failed (--strict treats warnings as errors)
```

即要挡住 CI 必须**显式**加 `--strict`；默认调用对警告放行。

> 原记录称校验为 `[实测]` 但把 `--strict` 与命令写在同一行，易被读成「已经用过 --strict」。
> 已核实参数存在，但本仓库当前调用未使用它。

## Agent 装配

- Markdown 格式：`~/.claude/agents/ast-*.md`
- 由 Claude Adapter 生成，带 YAML frontmatter（`name` / `description` / `model` / `skills`）
- 可委派的角色不带 `disallowedTools: Agent`；叶子 Agent 与 Governor 带

**核实**（`[官方]`，[sub-agents 文档](https://code.claude.com/docs/en/sub-agents)）：

> Subagents are Markdown files with YAML frontmatter.
> `.claude/agents/` → Current project；`~/.claude/agents/` → All your projects
> Only `name` and `description` are required.

`disallowedTools`、`model`、`skills` 均为官方支持的 frontmatter 字段（`model` 接受
`sonnet`/`opus`/`haiku`/`fable`/完整模型 ID/`inherit`）。本仓库 Adapter 用的
`model: inherit`、`disallowedTools: Agent`、`skills:` 三种写法**均为合法字段**，机制结论成立。

`[官方]` 补充两处本项目尚未覆盖的约束：

1. **`name` 不得含 `:`**（保留给 plugin 作用域标识，如 `my-plugin:reviewer`）；含 `:` 的文件
   不会被加载，且只写 debug 日志。
2. **plugin 来源的 subagent 不支持 `hooks` / `mcpServers` / `permissionMode`**，这三个字段在
   从 plugin 加载时被忽略。若将来把 Agent 改走 plugin 分发，需注意此项降级。

会话内校验 Agent 目录（`[官方]`，需 v2.1.233+）：

```bash
claude plugin validate ~/.claude/agents
```

## 本仓库的装配方式

安装器路径：`--tool claude-code --install --connect`，写 `~/.claude/agents/` 与 `~/.claude/skills/`。
实测写入 170 个技能目录。

**技能根核实**（`[官方]`，[skills 文档](https://code.claude.com/docs/en/skills)）：`~/.claude/skills/`
是**个人级技能根之一**，其余为项目级 `.claude/skills/`、企业级（managed settings 目录）、嵌套、
`--add-dir` 附加目录。优先级：企业 > 个人 > 项目。
故「技能根 = `~/.claude/skills/`」的原表述**方向正确但不完整**——它是个人级而非唯一根；
本仓库安装器写这个位置是对的。

**未使用插件路径**：`plugins/` 下目前只有 Codex 形态的包。**若要集中化五个包**，
按上文「单 marketplace 多插件」结论，需要为每个包新增 Claude 形态的目录
（`.claude-plugin/plugin.json` + `skills/`），并在 `.claude-plugin/marketplace.json` 的 `plugins[]`
里逐个写 `"source": "./plugins/<name>"`。**不要依赖 `metadata.pluginRoot`。**

> 现状提醒：仓库当前 `.claude-plugin/marketplace.json` 只有 1 个 entry，`source: "./"`；
> 其自带的 `.claude-plugin/plugin.json` 也在仓库根，因此该 entry 指向的是**仓库根**，
> 与 `plugins/` 下的 Codex 包无关。

## 相关文档

- [装配机制总览](./README.md)
- [Codex 装配](./adapter-codex.md)
- [Claude Code 插件市场官方文档](https://code.claude.com/docs/en/plugin-marketplaces)
- [Claude Code 插件参考（plugin.json / validate / 组件）](https://code.claude.com/docs/en/plugins-reference)
- [Claude Code 子代理（Agent 格式）](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Skills（技能根）](https://code.claude.com/docs/en/skills)
