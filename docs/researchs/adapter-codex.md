# Codex 装配

Codex 的接入已有**端到端实测**，是本仓库当前验证最充分的路径。

> **证据等级图例**：`[官方]` = OpenAI 官方文档（附 URL）；`[实测]` = 本机 codex 实跑（附命令/输出）；
> `[推定]` = 由上述两者推导；`[无法证实]` = 查不到，并列出搜过的关键词。
> 本轮独立复核环境：`codex-cli 0.154.0-alpha.6.2`（`/Applications/ChatGPT.app/Contents/Resources/codex`），
> 全部实测在 `CODEX_HOME=<临时目录>` 隔离下进行，未触碰真实 `~/.codex`。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| 插件市场 | `codex plugin marketplace add owner/repo` | `[官方]` `[实测]` **已核实** |
| 仓库级 marketplace | `$REPO_ROOT/.agents/plugins/marketplace.json` | `[官方]` **已核实** |
| 列插件 | `codex plugin list` | `[官方]` `[实测]` **已核实** |
| 装插件 | `codex plugin add <name>@<marketplace>` | `[官方]` `[实测]` **已核实** |
| 插件缓存 | `~/.codex/plugins/cache/$MARKETPLACE/$PLUGIN/$VERSION/` | `[官方]` `[实测]` **已修正**（见下） |
| 技能根 | `~/.agents/skills/` | `[官方]` `[实测]` **已核实** |

### 逐条核实（本轮）

**① `codex plugin marketplace add owner/repo` — 属实。**

`[实测]` `codex plugin marketplace add --help` 的 `<SOURCE>` 说明逐字列出四种来源：

```
Marketplace source: a local path, owner/repo[@ref], HTTPS Git URL, or SSH Git URL
```

`[实测]` 实跑远端仓库成功：

```bash
CODEX_HOME=/tmp/sp-plain codex plugin marketplace add hashgraph-online/awesome-codex-plugins
Added marketplace `awesome-codex-plugins` from https://github.com/hashgraph-online/awesome-codex-plugins.git.
```

`[官方]` 同一页给出四种来源与 `--ref`/`--sparse` 用法：
<https://developers.openai.com/plugins/build/plugins>（"Add a marketplace from the CLI"）

> **补充（local path 可作 source）——原文未写，已补**：**本地路径完全合法**，且是官方文档并列的
> 一等公民。`[官方]` 文档示例：`codex plugin marketplace add ./local-marketplace-root`；
> 来源列表写明 "local marketplace root directories"。`[实测]` 本仓库 `add .` 直接成功
> （见下方实测记录）。注意两点：① local 源上 `--ref`/`--sparse` **会被拒绝**，
> `[实测]` 报 `Error: --ref is only supported for git marketplace sources`；
> ② 传入的相对路径会被解析成绝对路径后再记录。

**② 仓库级 marketplace 位置 — 属实。**

`[官方]` 逐字确认 `$REPO_ROOT/.agents/plugins/marketplace.json`，与个人级
`~/.agents/plugins/marketplace.json` 并列，另有 legacy 兼容位
`$REPO_ROOT/.claude-plugin/marketplace.json`：

> "The ChatGPT desktop app can read marketplace files from: a repo marketplace at
> `$REPO_ROOT/.agents/plugins/marketplace.json`; a legacy-compatible marketplace at
> `$REPO_ROOT/.claude-plugin/marketplace.json`; a personal marketplace at
> `~/.agents/plugins/marketplace.json`"

<https://developers.openai.com/plugins/build/plugins>

`[实测]` 本仓库 `plugin list` 回显的正是该路径（见下方实测记录）。

**③ `codex plugin add <name>@<marketplace>` — 属实。**

`[实测]` `codex plugin add --help`：

```
Usage: codex plugin add [OPTIONS] <PLUGIN[@MARKETPLACE]>
  -m, --marketplace <MARKETPLACE>  Marketplace name to use when PLUGIN does not include @MARKETPLACE
```

`[官方]` openai/codex PR #21396 的 CLI 契约列出等价两种写法
（`codex plugin add <plugin>@<marketplace>` / `codex plugin add <plugin> --marketplace <marketplace>`）：
<https://github.com/openai/codex/pull/21396>

**④ 插件缓存路径 — 属实，但 `$VERSION` 的来源需修正。**

`[官方]` 原文：

> "ChatGPT installs plugins into `~/.codex/plugins/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION/`.
> For local plugins, `$VERSION` is `local`"

`[实测]` 实际落盘在 `$CODEX_HOME/plugins/cache/...`（`CODEX_HOME` 未设时才等于 `~/.codex`），
所以更准确的写法是 `$CODEX_HOME/plugins/cache/$MARKETPLACE/$PLUGIN/$VERSION/`。

**`$VERSION` 取自插件自己的 `.codex-plugin/plugin.json` 的 `version` 字段，不是 marketplace 条目里的 `version`。**
`[实测]` 对照（同一路径、只翻转插件内 `.codex-plugin/`）：

| 插件内 `.codex-plugin/plugin.json` | 落盘目录 |
|---|---|
| 存在，`"version":"1.6.0"` | `.../agi-super-team-codex/**1.6.0**` |
| 删除后（marketplace 条目 `version` 仍在） | `.../agi-super-team-codex/**local**` |

`[实测]` 把插件内版本改成 `9.9.9` 后：

```bash
codex plugin add agi-super-team-codex@agi-super-team
Installed plugin root: /private/tmp/vtest-home/plugins/cache/agi-super-team/agi-super-team-codex/9.9.9
```

**⑤ 技能根 `~/.agents/skills/` — 属实（就本项目配置而言）。**

`[官方]` 无单独的"技能根"条目；但本项目 `config/cli-adapters.json` 的 codex 条目
`skillPaths` 就是 `[".agents/skills"]`，`[实测]` codex 二进制内亦含 `.agents/skills` 字面量。
故这是**本项目自己的约定**，而非 Codex 强制的全局技能目录——表述上宜降级为
`[实测]`（本项目配置）而非 `[官方]`。

### 关于 `.codex-plugin/plugin.json`（**已修正：同名两个目录必须分开说**）

原文把这句写成了一个结论，但它其实混了两件不同的事。**仓库里有同名两处 `.codex-plugin/`，
作用完全相反**，必须分开表述：

| 位置 | 作用 | 证据 |
|---|---|---|
| `plugins/<name>/.codex-plugin/plugin.json`（**插件级**） | **必需的主清单**，决定 package 身份/版本/skills 根 | `[官方]` `[实测]` |
| `.codex-plugin/plugin.json`（**仓库根级**） | **无作用**，Codex 不读 | `[实测]` |

**插件级的那个是主清单，不是"兼容回退"。** `[官方]` 现行文档的措辞是：

> "Every plugin has a `.codex-plugin/plugin.json` manifest."
> "`.codex-plugin/plugin.json` is the required entry point."

<https://developers.openai.com/plugins/build/plugins>

`[实测]` 删掉插件级 `.codex-plugin/` 后，`plugin add` 的落盘版本从 `1.6.0` 塌成 `local`
（见上表 `$VERSION` 对照节），直接证明它在链路里是**承重**的，而非可选回退。

**原文引用的「remain supported as a compatibility fallback」确实存在、确实来自官方，但语境不同**，
不能拿来支撑"它对本机制不是必需"。`[官方]` 原文完整句是：

> "For a portable Agent Plugins package, add `plugin.json` at the plugin root and declare the
> Agent Plugins schema. … Existing `.codex-plugin/plugin.json` files remain supported as a
> compatibility fallback."

也就是说：**这是较新的「portable Agent Plugins」布局（根级 `plugin.json` 为主）出现后**，
`.codex-plugin/plugin.json` 才被降级为回退。在 0.154.0 上该新布局**已可用但不是唯一路径**——
`[实测]` 只放根级 `plugin.json`（无 `.codex-plugin/`）也能装，且**marketplace 条目自带 `version`
时即使完全没有清单文件也能装**：

```bash
# 插件级只有 plugin.json（portable 布局）
codex plugin add root-manifest@mtest
Installed plugin root: .../plugins/cache/mtest/root-manifest/7.7.7   # 取自 marketplace 条目 version

# 完全没有清单文件
codex plugin add no-manifest@mtest
Installed plugin root: .../plugins/cache/mtest/no-manifest/8.8.8
```

结论：**"必需"是相对于当前主布局（`.codex-plugin/`）说的；"回退"是相对于未来 portable 布局说的。
两种说法都不错，但不能混用。** 对本仓库而言，`plugins/agi-super-team-codex/.codex-plugin/plugin.json`
是当前唯一提供版本号的来源，删掉它会退化到 `local`。

#### 仓库根级 `.codex-plugin/` — 原文结论**成立**，本轮独立复核通过

原文称 commit `d955d891` 实测过"移除根级 `.codex-plugin/` 前后 `codex plugin add` 输出逐字相同"。
本轮用**同一路径**（避免路径前缀差异污染 diff）重做对照实验，四组变体
（根级有/无 × 插件级有/无）全跑，根级这一维确实**完全无影响**：

```bash
# 同一目录 /tmp/ab，先用 HEAD（无根级 .codex-plugin）跑完整三步
# 再把 d955d891^ 的根级 .codex-plugin/plugin.json 放回去，重跑
diff <(run-without-root) <(run-with-with-root)
# => IDENTICAL（0 字节差异，含 marketplace add / plugin list / plugin add 三段）
```

`[实测]` 结论：**根级 `.codex-plugin/` 对 Codex 的插件发现无作用，原文结论成立。**
补充机制解释：Codex 只从 marketplace 条目的 `source.path` 定位插件根，再在**该插件根**下找
`.codex-plugin/plugin.json`（`strings codex` 可见 `plugin_root / ".codex-plugin" / "plugin.json"`），
仓库根从不参与插件发现，因此根级那份天然是死文件。

本仓库**已删除**根级 `.codex-plugin/`（它是 `plugins/agi-super-team-codex/` 的重复副本）——**这一步无风险，保持删除**。

## 实测记录

> **已修正**：原文标注 `codex-cli 0.153.4`，本轮复核机上是 `codex-cli 0.154.0-alpha.6.2`。
> 下列输出为本轮在该版本上的重跑结果（与原文一致处保留，差异已标注）。

```bash
git archive HEAD | (mkdir -p /tmp/probe && tar -x -C /tmp/probe)
cd /tmp/probe
CODEX_HOME=/tmp/probe-home codex plugin marketplace add .
```

```
Added marketplace `agi-super-team` from /tmp/probe.
Installed marketplace root: /tmp/probe
```

```bash
CODEX_HOME=/tmp/probe-home codex plugin list
```

```
Marketplace `agi-super-team`
  /tmp/probe/.agents/plugins/marketplace.json

PLUGIN                               STATUS         VERSION  SOURCE
agi-super-team-codex@agi-super-team  not installed           /tmp/probe/plugins/agi-super-team-codex
```

> `VERSION` 列为空是本环境的正常表现：该列只在**远端 marketplace** 会预填版本号；
> 本地源要等 `plugin add` 读了插件清单才知道版本。

```bash
CODEX_HOME=/tmp/probe-home codex plugin add agi-super-team-codex@agi-super-team
```

```
Added plugin `agi-super-team-codex` from marketplace `agi-super-team`.
Installed plugin root: ~/.codex/plugins/cache/agi-super-team/agi-super-team-codex/1.6.0
```

> 原文末行的 `1.6.0` 在隔离实测中写为 `$CODEX_HOME/plugins/cache/...`（`CODEX_HOME` 未设时才等于 `~/.codex`）。

### 多插件集中化：一个 marketplace 放多个插件（**关键结论，原文缺失，已补**）

> 这条是评估"五包集中化"的关键输入，**本轮专门验证：完全可行。**
> `[官方]` "You don't need a separate marketplace per plugin. One marketplace can expose a
> single plugin while you are testing, then grow into a larger curated catalog as you add more plugins."
> <https://developers.openai.com/plugins/build/plugins>

`[实测]` 在 `.agents/plugins/marketplace.json` 的 `plugins[]` 放 3 个条目，
各自 `source.path` 指向**不同子目录**，全部被正确识别、分别安装到各自版本目录：

```json
{ "name": "q7-market",
  "plugins": [
    { "name": "agi-super-team-codex", "source": { "source": "local", "path": "./plugins/agi-super-team-codex" }, ... },
    { "name": "pack-bravo",           "source": { "source": "local", "path": "./plugins/pack-bravo" },           ... },
    { "name": "pack-charlie",         "source": { "source": "local", "path": "./plugins/pack-charlie" },         ... }
  ] }
```

```
$ codex plugin list
PLUGIN                          STATUS         VERSION  SOURCE
agi-super-team-codex@q7-market  not installed           /private/tmp/q7/plugins/agi-super-team-codex
pack-bravo@q7-market            not installed           /private/tmp/q7/plugins/pack-bravo
pack-charlie@q7-market          not installed           /private/tmp/q7/plugins/pack-charlie

$ codex plugin add pack-bravo@q7-market
Installed plugin root: .../plugins/cache/q7-market/pack-bravo/2.3.4
$ codex plugin add pack-charlie@q7-market
Installed plugin root: .../plugins/cache/q7-market/pack-charlie/2.3.4
```

**结论：`plugins[]` 支持任意多个插件，每个 `source.path` 可指向不同子目录，互不干扰。**
集中化的唯一约束是 `source.path` 必须 `./` 前缀且相对 marketplace root——
`[官方]` "point each `source.path` at the plugin folder with a `./`-prefixed path relative to the
marketplace root"；另见 issue 提示 "Local sources must stay under the marketplace directory"。

### `--ref` 与 `--sparse` 语义（**原文缺失，已补**）

`[官方]` 定义（<https://developers.openai.com/plugins/build/plugins>）：

> "Marketplace sources can be GitHub shorthand (`owner/repo` or `owner/repo@ref`), HTTP or HTTPS
> Git URLs, SSH Git URLs, or local marketplace root directories. Use `--ref` to pin a Git ref,
> and repeat `--sparse PATH` to use a sparse checkout for Git-backed marketplace repos.
> `--sparse` is valid only for Git marketplace sources."

`[实测]` 逐条验证：

| 结论 | 结果 |
|---|---|
| `--ref <REF>` = 锁定 Git ref（分支/tag/commit） | **属实**，回显带 `#main`：<br>`Added marketplace \`awesome-codex-plugins\` from https://github.com/hashgraph-online/awesome-codex-plugins.git#main.` |
| `--ref` 限 Git 源 | **属实**，`[实测]` local 源报 `Error: --ref is only supported for git marketplace sources`（连"本地路径恰好是 git 仓库"也被拒） |
| `--sparse <PATH>` = 稀疏检出，可重复 | **属实**，且**必须把 manifest 所在目录也纳入** |
| `--sparse` 能否"只取 `plugins/<name>` 子目录" | **不能单独用**——见下 |

`[实测]` `--sparse` 的坑（原文未提，**建包时必须知道**）：

```bash
# 只取插件目录 → 失败，因为 manifest 没被检出
codex plugin marketplace add owner/repo --sparse plugins
Error: invalid marketplace file `.../.staging/marketplace-add-XXXX`:
       marketplace root does not contain a supported manifest

# manifest 目录 + 插件目录一起取 → 成功
codex plugin marketplace add owner/repo --sparse .agents/plugins --sparse plugins
Added marketplace `awesome-codex-plugins` from https://github.com/hashgraph-online/awesome-codex-plugins.git.
```

**即：`--sparse` 每次都必须显式包含 `.agents/plugins`，否则 sparse 副本里没有 marketplace.json，
整个 marketplace 直接不可用。** 想只拉某一个插件子目录，正确写法是
`--sparse .agents/plugins --sparse plugins/<name>`，而不是只写 `plugins/<name>`。
（`[官方]` 示例本身也印证这点：`codex plugin marketplace add <source> --sparse .agents/plugins`
——详见 openai/codex#21396 与文档页。）

### 删除根级 `.codex-plugin/` 的对照实验

同一组命令在**有**根级 `.codex-plugin/` 与**删除后**的两个副本上分别执行，`plugin list` 与 `plugin add` 输出**逐字相同**，插件均正常安装。

结论：该目录对 Codex 的插件发现无作用。

## Agent 装配（`[实测]` 已核实，来源=本仓库代码）

- Codex 使用 **TOML** 格式的 agent 文件：`~/.codex/agents/ast-*.toml`
  —— `[实测]` `bin/adapters/codex.mjs:101` 写 `join(tool.agentPaths[0], \`ast-${agent.id}.toml\`)`，
  而 `agentPaths[0]` = `.codex/agents`；另在 `dirname(agentPaths[0])` 下写 `AGENTS.md` 与 `config.toml`。
- 主会话本身承担 CEO，**不生成第二个 CEO Agent**
  —— `[实测]` `bin/adapters/codex.mjs:18` 注释逐字印证：
  "Codex 的 root session 本身就是 CEO（本 adapter 不写 ast-ceo.toml）"。
- 当前主会话是 CEO，其余角色以 TOML 呈现 —— 同上。

## 本仓库的装配方式

两种并存：

1. **安装器路径** —— `--tool codex --install`，写 `~/.agents/skills/` 与 `~/.codex/agents/*.toml`
2. **插件路径** —— 通过 `.agents/plugins/marketplace.json` 走 Codex 原生插件安装

### 附带收益（**已修正：DSH/Kimi 那半句不成立**）

Codex 安装器的技能落盘位置是 `~/.agents/skills/`（`[实测]` 本项目 `config/cli-adapters.json`
的 codex 条目 `skillPaths: [".agents/skills"]`）。实测：`--tool codex --install` 写入 170 个技能目录。

> **原文称该目录"同时被 DSH 和 Kimi 读取"——本轮复核判定不成立。**
> `[实测]` `config/cli-adapters.json` 共 18 个目标，**没有 `dsh` 也没有 `kimi` 条目**
> （`grep -c "dsh\|kimi" config/cli-adapters.json` → `0`）。18 个 id 为：
> `claude-code, codex, openclaw, hermes, copilot, antigravity, gemini-cli, opencode,
> cursor, trae, aider, windsurf, qwen, deerflow, workbuddy, codewhale, kiro, qoder`。
> 其中 `skillPaths` 指向 `.agents/skills` 的**只有 codex 一个**；openclaw / hermes 走
> `skills/agi-super-team`。
> `[无法证实]` 未能在本仓库内找到任何 DSH 或 Kimi 读取 `~/.agents/skills/` 的证据。
> 搜过的关键词：`dsh|kimi`（全仓 `config/`、`bin/`）、`agents/skills`（`config/`、`bin/`、`tests/`）、
> tavily：`"~/.agents/skills" DSH Kimi shared skill root`、`Codex plugin skills .agents/skills cross-harness`。
> **建议**：删掉这半句，或改写成 `[推定]` 并注明"未经实测证实"。

## 相关文档

- [装配机制总览](./README.md)
- [Claude Code 装配](./adapter-claude-code.md)
- [Adapter 注册机制](../architecture/adapter-registration.md)
