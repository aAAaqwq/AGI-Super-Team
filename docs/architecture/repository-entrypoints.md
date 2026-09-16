# 仓库入口地图：三层结构与 harness 入口对照

这份文档回答一个具体问题：**仓库根目录下那些以点开头的 harness 目录，各自是给谁用的、删掉会怎样。**

它不重复 [Adapter 注册机制](./adapter-registration.md) 讲的代码层注册与校验，也不重复 [仓库架构地图](./repository-architecture.md) 讲的五层归属。本文只讲**入口**——从仓库根到用户桌面之间的那几道门。

## 三层结构：canonical → 分发 → 文档

仓库的入口不是一层，而是三层，**改动必须沿同一方向流动**：

| 层 | 载体 | 性质 | 谁读它 |
|---|---|---|---|
| ① **canonical**（权威源） | [`agents/`](../../agents/) · [`skills/`](../../skills/) · [`config/`](../../config/) | 手写，唯一真相 | 构建脚本、维护者 |
| ② **分发入口** | 根级 harness 清单目录 + [`plugins/`](../../plugins/) + `bin/installer/` | 多为**机器必需**的注册声明 | 各 harness 客户端 |
| ③ **用户文档** | [`docs/`](.) · [`cookbook/`](../../cookbook/) · 根级 README | 任人阅读，非权威 | 人类 |

**关键约束**：canonical 只向分发层单向流出。分发入口是客户端强制的位置和格式，**不是**可以随手重构的目录——改一个点目录的路径或内容，等于改一个客户端的加载契约。这就是下方表中「删除后果」一列存在的原因。

## 六个 harness 入口对照表

证据等级：`[实测]` = 本机实际跑过并观察到结果；`[官方]` = 已比对**官方文档/官方 Schema 原文**（不再等同于「有依据」——本轮把「位置合法」与「字段合法」拆成两列）；`[未证实]` = 仓库里有该文件，但**没有任何证据**表明有客户端真的读它。

| 入口 | 服务 | 机器必需 / 人类阅读 | 删除后果 | 证据 |
|---|---|---|---|---|
| [`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json) | Claude Code | **机器必需** | `claude plugin marketplace add` 直接失败（`✘ Failed to add marketplace`），无法安装 | `[实测]` |
| [`.agents/plugins/marketplace.json`](../../.agents/plugins/marketplace.json) | **Codex**（非共享，见下节） | **机器必需** | Codex 无法解析本仓库的 marketplace；内容声明 `plugins/` 下的五个精选包 | `[实测]` |
| [`.codex/INDEX.md`](../../.codex/INDEX.md) | Codex | **仅人类** | 无代码读取，仅丢失一段人工安装指引；Codex 不会因此报错 | `[实测]` |
| [`.cursor-plugin/plugin.json`](../../.cursor-plugin/plugin.json) | Cursor | 机器声明 | 无已知破坏。**字段违规已修**：`skillsDir`→`skills`（官方字段名）、移除越界的 `author.url`（官方 `author` 为 `additionalProperties: false`，仅 `name`/`email`）。客户端是否真加载仍 `[未证实]`。见 [调研文档](../researchs/adapter-cursor.md) | `[官方]` 位置+字段合法 / `[未证实]` 端到端 |
| [`.kimi-plugin/plugin.json`](../../.kimi-plugin/plugin.json) | Kimi | 机器声明，**仅作安装源** | 无已知破坏；官方明示插件**不支持项目级作用域**、CLI 只跑托管副本，故该文件**不会被自动读取**，只在 `/plugins install` 时被消费 | `[官方]` 位置+字段合法 / `[官方]` **不自动生效** |
| [`gemini-extension.json`](../../gemini-extension.json) | Gemini CLI | 机器声明 | 无已知破坏；官方机制是 `gemini extensions install` 克隆整仓后从**绝对根**读 manifest，本仓库满足该前提 | `[官方]` 位置+字段合法 / `[推定]` 端到端 |

### 这张表为什么重要

六个入口里只有 **两个**有端到端实测证据。其余四个要分成三种**性质完全不同**的情况，不能笼统写成「声明性存在」：

| 情况 | 入口 | 判据 |
|---|---|---|
| **位置与字段都合法，机制可解释** | `gemini-extension.json` | `contextFileName` 是官方字段名且值合法；官方 install 流程会把仓库克隆到扩展目录，`CLAUDE.md` 随克隆落地 |
| **位置与字段都合法，但客户端是否读取未证实** | `.cursor-plugin/plugin.json` | 字段违规已于核实后修复（`skillsDir`→`skills`、移除 `author.url`）；本机无 Cursor，端到端未验证 |
| **位置与字段都合法，但客户端不自动读** | `.kimi-plugin/plugin.json` | 官方明示「暂不支持项目级安装范围」+「CLI 始终从托管副本运行」→ 仓库里的 manifest 只能作为安装源 |

把它们写成「支持的入口」会制造虚假能力声明。本仓库的定位是 evidence-backed——**入口存在 ≠ 字段合法 ≠ 客户端会读**，三者必须分开陈述。本轮的两步：先发现 `.cursor-plugin/` 带着官方 schema 不认可的字段（位置合法 ≠ 字段合法），修复后它与 `.kimi-plugin/`/`gemini-extension.json` 归为同一性质——**位置与字段都合法，但客户端是否真的读取尚无证据**。

`.cursor-plugin/`、`.kimi-plugin/`、`gemini-extension.json` 三者在 [`config/repository-architecture.json`](../../config/repository-architecture.json) 中均标为 `evidenceStatus: "pending"`（`.claude-plugin` 标为 `legacy`，`.agents` 标为 `manifest`）。**注册表未改动**——本轮只补文档层结论；是否把 `pending` 细化为「invalid / no-auto-discovery / documented」需维护者决定。

> 逐条核实的原文引用与检索记录见各框架调研文档：[Cursor](../researchs/adapter-cursor.md) · [Gemini](../researchs/adapter-gemini.md) · [Kimi](../researchs/adapter-kimi.md)。

## ⚠️ 最容易混淆的一点：`.agents/` ≠ `~/.agents/skills/`

**这两个路径名字很像，但毫无关系。** 用户已经因此问过一次，这里明确点破：

| | 仓库内的 `.agents/` | 用户主机的 `~/.agents/skills/` |
|---|---|---|
| 位置 | 本仓库根目录，**随仓库分发** | 用户 home 目录，**与本仓库无关** |
| 内容 | 只有一个文件：`plugins/marketplace.json` | 跨工具共享的 Skill 目录，一堆技能 |
| 用途 | **Codex 的 marketplace 注册** | Codex / DSH / Kimi 等工具读取的**共享技能池** |
| 谁读 | Codex 客户端 | 各 harness 客户端按自己的规则读取 |
| 关系 | 无 | 无 |

**一句话**：仓库里的 `.agents/` 是**注册声明**，主机上的 `~/.agents/skills/` 是**技能存放地**。看到仓库里的 `.agents/` 就以为「这是给用户共享技能用的」是错的——它只声明 Codex 插件。

验证方式：`find .agents -type f` 在本仓库只返回一个文件，即 `.agents/plugins/marketplace.json`。（该文件**声明**五个精选包，但目录里仍然只有这一个文件。）

## 第二层入口：`plugins/` 的五个精选包

`plugins/` 下是**精选分发包**（curated package），是给「用 harness 自带插件市场安装」的用户走的第二条发现路径。它们不是必需入口——`npx agi-super-team --tool <id>` 仍然是所有 harness 的主路径。

| 包 | 清单 | 内容 | 生成器 |
|---|---|---|---|
| [`plugins/agi-super-team-codex`](../../plugins/agi-super-team-codex/) | `.codex-plugin/plugin.json` | 6 个 Skill + 136 个 agent TOML | `scripts/build_codex_csuite_adapter.py` |
| [`plugins/agi-super-team-claudecode`](../../plugins/agi-super-team-claudecode/) | `.claude-plugin/plugin.json` | 14 个 agent 定义 + orchestrator Skill + connection spec | `scripts/build_claudecode_package.py` |
| [`plugins/agi-super-team-hermes`](../../plugins/agi-super-team-hermes/) | `plugin.json` | 14 个 role Skill + 14 个 Profile 蓝图 + connection spec | `scripts/build_hermes_package.py` |
| [`plugins/agi-super-team-dsh`](../../plugins/agi-super-team-dsh/) | `dsh-plugin.json` | 指令链 + profile patch + agent preset，共 19 个文件 | `scripts/build_dsh_package.py` |
| [`plugins/agi-super-team-openclaw`](../../plugins/agi-super-team-openclaw/) | `openclaw.plugin.json` | 84 个 workspace 文件 + connection spec | `scripts/build_openclaw_package.py` |

**四个 per-harness 包的产物来自 harness 自己的 Adapter**：生成器不重写渲染逻辑，而是经 [`scripts/util/render_harness_artifacts.mjs`](../../scripts/util/render_harness_artifacts.mjs) 调用 `bin/adapters/<id>.mjs` 的 `renderAdapterArtifacts` / `buildConnectionSpec`，再把绝对路径改写为包相对路径。每个 `tests/test_<harness>_package.py` 都用 `--check` 断言入库产物仍与该 Adapter 逐字一致——改了 Adapter 忘了重跑生成器，测试会红。

**精选包不打包 skills**：Skills 是 canonical 内容，由安装器从唯一的 `skills/` 根发放；复制进四个包等于把 canonical 源重复四份，违反 [ADR-0002](../adr/0002-generic-workspace-and-curated-distributions.md)。包只装 harness 专属层（agent 定义 / profile / preset / connection spec），每个包自带的那一个 SKILL.md 是 Adapter 生成的 orchestrator 入口，不是拷贝。原因详见 [`plugins/README.md`](../../plugins/README.md)。

## 与 canonical 层的接缝

分发入口不产生权威内容，只做翻译：

- `config/team-manifest.json` → `bin/installer/` → 各 harness 的原生产物
- `config/cli-adapters.json` → [`bin/installer/catalog.mjs`](../../bin/installer/catalog.mjs) → 19 个 CLI 目标（**恰好 19 个**，三处硬校验，见 [Adapter 注册机制](./adapter-registration.md)）
- 五个主力框架额外有 `config/harness-adapters/<id>.json` + `bin/adapters/<id>.mjs`
- `plugins/` 的四个 per-harness 包 → `scripts/build_<harness>_package.py` → 同一个 `bin/adapters/<id>.mjs`（**同一真源，不是第二套渲染**）

具体落盘位置与接线行为见 [主力框架接入手册](../guides/harness-adapters.md)；逐框架的调研结论见 [各 Coding Agent 的装配机制](../researchs/coding-agent-assembly.md)。

## 已修正的一处描述

1. **名不副实（已修正）**：[`docs/architecture/repository-architecture.md`](./repository-architecture.md) 曾把 `.agents/` 描述为 "shared repo marketplace"，但该文件实际只是**一个 marketplace 注册声明**（见上表）。该行已拆为两条，并删去 "shared" 这一与内容不符的措辞。

## 记录：一处曾误判、实际不成立的「矛盾」

`config/repository-architecture.json` 给 `.codex` 的 `role` 是 `public-navigation`、`module` 是 `distribution-adapters`。这**曾**被判断为 role/module 语义冲突，**该判断是错的**：

**`role` 与 `module` 是正交的两维** —— 前者答「这是什么性质的产物」，后者答「归哪个子系统所有」。同一条目上二者不同是正常且普遍的：

| 条目 | role | module |
|---|---|---|
| `README.md` | public-navigation | public-navigation |
| `AGENTS.md` | public-navigation | governance-memory |
| `.codex` | public-navigation | distribution-adapters |

`.codex/` 是**面向人类**的 Codex 安装指引（role），同时**归属分发适配器子系统**（module）—— 两个判断都成立。

判定依据：把它改成 `module: public-navigation` 会直接破坏架构自检 —— `audit_architecture.py` 报 `module distribution-adapters implementation lacks matching ownership: .codex`，契约测试（95 分门槛）随即失败。**注册表原值正确，未做改动。**


## 返回

- [文档索引](../README.md)
- [仓库架构地图](./repository-architecture.md)
- [Adapter 注册机制](./adapter-registration.md)
