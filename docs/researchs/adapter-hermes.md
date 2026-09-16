# Hermes 装配

> **核实记录**：2026-09-16 用 tavily 检索官方文档站 + 官方仓库源码 + 本机落盘产物逐条核实。
> 证据等级：`[官方]`（附 URL）/ `[实测]`（附命令与输出）/ `[推定]` / `[无法证实]`。
>
> **查证时官方最新 tag 为 `v2026.9.14`**，本文所引文档站为 main 线。`guides/harness-adapters.md`
> 引用的 `v2026.8.3`（commit `3c27eb6…`）仍然有效、无幻觉，但已经不是最新——见文末「版本化依据」。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| 插件安装 | `hermes plugins install owner/repo --no-enable` | `[官方]` <https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins> |
| 列出 | `hermes plugins list` | `[官方]` <https://hermes-agent.nousresearch.com/docs/reference/cli-commands> |
| 启用 | `hermes plugins enable <name>` | `[官方]` 同上（CLI reference 逐字给出 `enable <name>`） |
| 技能根 | `~/.hermes/skills/` | `[官方]` <https://hermes-agent.nousresearch.com/docs/user-guide/features/skills> + `[实测]` 本机 `~/.hermes/skills/` 已落盘 |
| 插件目录 | `~/.hermes/plugins/` | `[官方]` <https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins>（discovery 表 `User` 行） |
| 技能安装 | `hermes skills install <id>` | `[官方]` <https://hermes-agent.nousresearch.com/docs/reference/cli-commands> |

> **已核实**：上表六条**全部成立**，无一条需要推翻。`hermes plugins {install,list,enable}`、
> `hermes skills install`、`~/.hermes/skills/`、`~/.hermes/plugins/` 六项均在官方文档逐字命中。
>
> **已补充**：`install <identifier>` 的实际参数形态比原表更宽 —— 支持 Git URL、
> `owner/repo`、以及**裸索引名**（无斜杠时经社区插件索引解析为 `owner/repo` + 索引钉住的 commit）。
> 另有 `--ref <40位SHA>`（只接受完整 40 位 commit，tag/分支/短 SHA 一律拒绝）用于可复现安装。
> `[官方]` <https://hermes-agent.nousresearch.com/docs/reference/cli-commands>
>
> **已补充**：`hermes plugins enable` 的实参是**插件名**（如 `observability/langfuse`），
> 原文写 `<plugin-name>` 是正确的。

### 安装后默认禁用

`hermes plugins install` 装完后插件**处于禁用状态**，必须显式 `hermes plugins enable` 才会生效。这是 Hermes 的设计，不是失败信号。

> **已核实，但需精确化**：官方原文是「**General plugins and user-installed backends are disabled by default**」，
> 且 `hermes plugins install owner/repo` 之后会**交互式问** `Enable 'name' now? [y/N]`（默认 No）。
> 也就是说默认禁用成立，但它是**可交互覆盖**的，不是强制两段式：
> - `--no-enable`：装完保持禁用，**跳过提问**（脚本化用）
> - `--enable`：装完直接启用，**跳过提问**
> - 不给标志：仍会问一句，默认答 No
>
> 另一条边界：**不是所有插件都受 `plugins.enabled` 白名单管**。Bundled platform plugins、
> bundled backends、memory providers、context engines、bundled model providers 属于
> 「always-works 基础设施」，**自动加载**，由各自的 `config.yaml` 键选择（如
> `memory.provider` / `context.engine` / `image_gen.provider`）。白名单只管第三方 general plugin
> 与用户自装的 platform adapter。
> `[官方]` <https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins>

### 可移植插件格式（Agent Plugins v1.0.0）

Hermes 能安装遵循 Agent Plugins v1.0.0 的目录包：

```text
my-portable-plugin/
├── plugin.json          ← 必须在插件包根目录
├── skills/
│   └── summarize/
│       ├── SKILL.md
│       └── references/
└── mcp.json             ← 可选
```

**注意**：`plugin.json` 必须在**插件包根目录**。这与本仓库现有的 `plugins/agi-super-team-codex/.codex-plugin/plugin.json` 布局不同。

> **已核实**：目录结构与官方逐字一致，含 `plugin.json` 在包根、`skills/<name>/SKILL.md`、
> 可选 `mcp.json` 三点。官方另有两点未写进本文，值得补：
> 1. **这是兼容适配层，不是 Hermes 原生插件**。原生插件是 `plugin.yaml` + `register(ctx)`；
>    portable 包官方定性为 "a compatibility adapter … does not replace native plugins"。
> 2. **Portable 包的 Skill 是只读的**，命名空间形如 `agent-plugin-<slug>-<hash>`，
>    经 `skills_list` / `skill_view` 装载；MCP 命令以「单 executable token + 独立参数数组」传递，
>    **永不过 shell**。`PLUGIN_ROOT` / `PLUGIN_DATA` 为注入的环境变量。
>
> 官方也再次确认了安装三段式：`install owner/repository --no-enable` → `list` → `enable <plugin-name>`。
> `[官方]` <https://hermes-agent.nousresearch.com/docs/developer-guide/plugins>

### 安全扫描

每次 `hermes plugins install` / `update` 都会对插件树跑**静态安全扫描**（凭据外泄、反弹 shell、破坏性命令、持久化机制、混淆执行、文档中的提示注入）。

三档判定，与 Cowork 的 pass/warn/fail 对应。插件读取自己声明的环境变量（`requires_env`）不会被误报。

> **已核实**：六类威胁模式、三档判定、`requires_env` 豁免**全部逐字命中官方文档**。
> 补两条边界：
> - 三档实际名为 **`safe` / `caution` / `dangerous`**（不是 pass/warn/fail；官方明说是
>   「matching Cowork's pass/warn/fail」，即对应而非同名）。
> - `caution` 可用 `--force` 覆盖；**`dangerous` 是硬阻断，`--force` 不能覆盖**。
>   `update` 时若新树被判 `dangerous`，插件会被**自动禁用**直到人工复核后重新启用。
> - 扫描默认开，可在 `config.yaml` 关：`plugins.scan_on_install: false`。
>
> `[官方]` <https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins>

### 环境变量

非空 `HERMES_HOME` 是最终安装根。未设置时 POSIX 默认 `~/.hermes`，Windows 默认 `%LOCALAPPDATA%\hermes`。

> **已核实，但需分层**（这一条是本次核实中精确度提升最大的一条）：
>
> 1. **POSIX 默认 `~/.hermes`、Windows 默认 `%LOCALAPPDATA%\hermes`** —— `[官方]` 文档
>    <https://hermes-agent.nousresearch.com/docs/reference/environment-variables> 与源码
>    <https://github.com/NousResearch/hermes-agent/blob/3c27eb6234bf91b8ceee9e9071591b31e9b148cb/hermes_constants.py#L53-L62>
>    一致。原结论成立。
> 2. **「非空即最终安装根」在文档层面成立**：老版源码 `_hermes_home_from_env()` 就是
>    `if val: return Path(val)` —— 无归一化、无校验。`[官方]`（同上源码链接）
> 3. **但当前 main 的 `get_hermes_home()` 是三段式解析**，不是两段式：
>    ① **context-local override**（`set_hermes_home_override()`，per-task/Profile 用，由 wrapper
>    脚本注入）→ ② `HERMES_HOME` 环境变量 → ③ 平台默认。
>    所以 `HERMES_HOME` 只是 **进程级** 答案，进程内可能被 override 覆盖。
>    `[官方]` <https://github.com/NousResearch/hermes-agent/blob/main/hermes_constants.py#L101-L109>
>    `[推定]` 安装器在 Preview 阶段是独立进程、不受 override 影响，因此「最终安装根」的结论
>    **对本仓库的安装器路径仍然成立**；但作为对 Hermes 的一般性描述已经不准确。
> 4. 与上面直接相关的一条坑（本文原先未提）：当 `HERMES_HOME` **未设置**但
>    `active_profile` 文件表明有非默认 Profile 处于 sticky-active 时，`get_hermes_home()`
>    会**静默回退到平台默认 home**，只在 `errors.log` 打一条一次性告警。
>    即「未设置 `HERMES_HOME` 却开了 Profile」= 跨 Profile 数据串档风险。
>    `[官方]`（同上源码 docstring）

**与 `--home` 冲突时安装器直接报错**：

```
error: --home conflicts with HERMES_HOME: /path/to/home
```

实测遇到过。两者只能给一个。

> **已修正（措辞）**：报错文本属实，两个细节要更正：
> - 冲突判据**不是**「两者同时给」，而是「`--home` 显式给出 **且** `HERMES_HOME` 解析出的目标
>   与 `--home` 推导的默认值**不一致**」。若两者恰好指向同一路径，**不报错**。
> - 该报错**不限于 `--home` 与 `HERMES_HOME`**，是 `harness-roots.mjs` 里一个通用 helper，
>   OpenClaw 的 `OPENCLAW_HOME` / `OPENCLAW_STATE_DIR` / `OPENCLAW_CONFIG_PATH` 与
>   Codex 的 `CODEX_HOME` 走同一逻辑、同一种报错格式。
>
> `[实测]` 本仓库源码：`bin/installer/harness-roots.mjs:29-32`
> （`requireAlignedExplicitHome()`，`throw new Error(\`--home conflicts with ${name}: ${actual}\`)`），
> 调用点 `harness-roots.mjs:51-53`；Codex 侧另有一份等价实现 `bin/agi-super-team.mjs:267`。

## 本仓库的装配方式

安装器路径：

```bash
npx -y agi-super-team@latest --tool hermes --install
```

- Agent 产物：`$HERMES_HOME/skills/agi-super-team-agents/ast-*/SKILL.md` + Profile 蓝图
- 技能产物：`$HERMES_HOME/skills/agi-super-team/<skill>`
- **不自动创建** Profile、Cron 或 Gateway

实测：隔离 HOME 下安装成功，写入 `~/.hermes/skills`。

> **已核实（本机落盘产物为证）**：本机 `~/.hermes/` 有一份真实安装（`receipt.json`：
> `packageVersion: 1.4.0`、`generatedAt: 2026-07-30T11:14:59Z`、`status: filesystem-connected`、
> `runtimeEvidence: pending`）。逐项对上：
> - `~/.hermes/skills/agi-super-team-agents/ast-*/SKILL.md` ✔（含 `ast-cto`、`ast-governor`、
>   `ast-cco-<specialist>` 等全量叶子）
> - `~/.hermes/skills/agi-super-team/<skill>` ✔
> - `~/.hermes/agi-super-team/profiles/ast-*/profile.json` ✔（14 个 C-suite/Governor）
> - `~/.hermes/agi-super-team/connection.json` + `receipt.json` ✔
> - **`~/.hermes/profiles/` 不存在** ✔ —— Profile 确**未**被创建，与「不自动创建 Profile」一致
>
> `[实测]` `ls -la ~/.hermes/`、`cat ~/.hermes/agi-super-team/receipt.json`。
>
> **已核实「Profile 蓝图」的官方依据**：Hermes 的 Profile 是**官方一等概念**
> （`hermes profile {list,use,create,delete,show,alias,rename,export,import,install,update,info}`，
> 每个 Profile 是独立 `HERMES_HOME`，有自己的 config/sessions/skills/gateway/persona），
> Kanban 也是官方一等概念（`hermes kanban`，多 Profile 协作板，任务按 `--assignee <profile>` 分派）。
> 因此本 Adapter 的 `adapterMode: "profiles-kanban"` 与蓝图产物**有官方机制支撑**。
> **但要注意边界**：Hermes **没有任何 `profile.json` 蓝图格式**——`profile.json` 是
> **本仓库自定义的产物**（`blueprintOnly: true` / `runtimeStateCreated: false`），
> 官方创建 Profile 的入口是 `hermes profile create <name>`。
> 即：**机制是官方的，蓝图文件格式是本仓库的**，两者不要混为一谈。
> `[官方]` Profile：<https://hermes-agent.nousresearch.com/docs/reference/profile-commands>；
> Kanban：<https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban>；
> `[实测]` 蓝图格式：本机 `~/.hermes/agi-super-team/profiles/ast-cto/profile.json`。

## `skills.external_dirs`（外部技能目录）

> **已核实**：`skills.external_dirs` **确是当前官方支持的外部技能目录机制**，无需修正。
> 在 `~/.hermes/config.yaml` 的 `skills:` 段下声明：
>
> ```yaml
> skills:
>   external_dirs:
>     - ~/.agents/skills
>     - /home/shared/team-skills
>     - ${SKILLS_REPO}/skills
> ```
>
> - 路径支持 `~` 展开与 `${VAR}` 环境变量替换；相对路径按 Hermes home 解析。
> - **语义（三条官方原话，与 `guides/harness-adapters.md` 的安全提示互相印证）**：
>   1. **「External dirs are not a write-protection boundary」** —— 只要 Hermes 进程对该目录有写权限，
>      agent 的 `skill_manage`（`patch`/`edit`/`write_file`/`remove_file`/`delete`）就能改动其中文件。
>      这**逐字证实**了 guide 里「该目录不是只读安全边界」的说法，guide 此处**无需更正**。
>   2. **Local precedence** —— 同名 Skill 本地 `~/.hermes/skills/` 胜出。
>   3. **不存在的路径静默跳过**（无报错）。
> - 外部目录里的 Skill 与本地 Skill 等价接入系统提示索引、`skills_list`、`skill_view` 与 `/skill-name`。
>
> `[官方]` <https://github.com/NousResearch/hermes-agent/blob/3c27eb6234bf91b8ceee9e9071591b31e9b148cb/website/docs/user-guide/features/skills.md#L315>（锚点 `#external-skill-directories`）
> 与文档站 <https://hermes-agent.nousresearch.com/docs/user-guide/features/skills>

### 版本化依据（`harness-adapters.md` 引用的链接是否仍然成立）

`guides/harness-adapters.md` 声称以官方 `v2026.8.3` 的 `get_hermes_home()` / `get_skills_dir()` 为准，
commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb`。逐项核实：

| 引用项 | 核实结果 |
|---|---|
| commit `3c27eb6…` 存在 | ✅ **成立**。`git ls-remote --tags` 证实它就是 `v2026.8.3^{}` 的 dereference 目标 |
| `hermes_constants.py` 中定义 `get_hermes_home()` | ✅ 成立（L114） |
| `get_hermes_home()` 行号 `L53-L74` | ❌ **已过时**。L53 是 `def _get_platform_default_hermes_home()`，L74 是 `return _get_platform_default_hermes_home()`。`get_hermes_home()` 本身在 **L114**，函数体到 L139 |
| `get_skills_dir()` 行号 `L1302-L1304` | ✅ **成立**（L1302 定义，L1302-1304 恰为三行函数体） |
| `get_skills_dir()` 语义 = `get_hermes_home() / "skills"` | ✅ 成立 |
| POSIX `~/.hermes` / Windows `%LOCALAPPDATA%\hermes` | ✅ 成立（L53-62） |
| `skills.external_dirs` 链接 | ✅ **成立**（见上节） |

**结论：链接和函数名没有幻觉，`get_skills_dir()` 的行号甚至完全准确；唯一错的是
`get_hermes_home()` 的行号（L53-L74 实际是平台默认 home 的 helper）。**

另需注意**版本已经落后**：核实当日（2026-09-16）官方最新 tag 是 **`v2026.9.14`**，
`v2026.8.3` 已落后约 6 周（中间有 8.13 / 8.16 / 8.16.2 / 8.18 / 8.19 / 8.27 / 8.31 / 9.7 / 9.11 / 9.14）。
且在 **main** 上 `hermes_constants.py` 已从 1481 行缩到 1299 行，`get_hermes_home()` 从 L114 移到 **L101**，
`get_skills_dir()` 从 L1302 移到 **L1144**。`get_skills_dir()` 的语义未变，
`get_hermes_home()` 的语义**变了**（见上文「环境变量」第 3 点：新增了 context-local override 段）。

> **建议**（按任务约定不改 `docs/guides/`，仅在此记录）：guide 里
> 「以 `v2026.8.3` 为准」这句**不算错**（引用对象真实存在且语义未失效），但
> ① `get_hermes_home()` 的行号引用应改为 `#L114-L139`；
> ② 若要反映当前行为，应升级到 `v2026.9.14` 并把行号改为 L101 / L1144；
> ③ `get_hermes_home()` 的「override → env → default」三段式解析值得补一句，
> 否则「非空 `HERMES_HOME` 即最终根」在 Profile 场景下会被误读。

## 未做的事

本仓库**未**提供 Hermes 形态的插件包（包根 `plugin.json`）。当前只走安装器。

若要支持 `hermes plugins install aAAaqwq/AGI-Super-Team`，需新增 `plugins/agi-super-team-hermes/`，且 `plugin.json` 放在包根而非 `.codex-plugin/` 子目录。

> **已核实**：此判断成立。Native 插件的包根是 `plugin.yaml`（+ `__init__.py` / `schemas.py` / `tools.py`），
> Portable 插件的包根是 `plugin.json`；两者都在**包根**，均非 `.codex-plugin/` 这类子目录。
> `[官方]` <https://hermes-agent.nousresearch.com/docs/developer-guide/plugins>

## 相关文档

- [装配机制总览](./README.md)
- [harness-adapters.md](../guides/harness-adapters.md) — `get_hermes_home()` 等版本化依据
- [Hermes — Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/)
- [Hermes — CLI Commands Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)
- [Hermes — Plugins（用户视角）](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
- [Hermes — Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Hermes — Environment Variables Reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables)
- [Hermes — Profile Commands Reference](https://hermes-agent.nousresearch.com/docs/reference/profile-commands)
- [Hermes — Kanban (Multi-Agent Board)](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban)
