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

证据等级：`[实测]` = 本机实际跑过并观察到结果；`[文档]` = 有官方或仓库内文档依据但未实测客户端行为；`[未证实]` = 仓库里有该文件，但**没有任何证据**表明有客户端真的读它。

| 入口 | 服务 | 机器必需 / 人类阅读 | 删除后果 | 证据 |
|---|---|---|---|---|
| [`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json) | Claude Code | **机器必需** | `claude plugin marketplace add` 直接失败（`✘ Failed to add marketplace`），无法安装 | `[实测]` |
| [`.agents/plugins/marketplace.json`](../../.agents/plugins/marketplace.json) | **Codex**（非共享，见下节） | **机器必需** | Codex 无法解析本仓库的 marketplace；内容只声明 `agi-super-team-codex` | `[实测]` |
| [`.codex/INDEX.md`](../../.codex/INDEX.md) | Codex | **仅人类** | 无代码读取，仅丢失一段人工安装指引；Codex 不会因此报错 | `[实测]` |
| [`.cursor-plugin/plugin.json`](../../.cursor-plugin/plugin.json) | Cursor | 机器声明，**未被证实读取** | 无已知破坏；仓库内无任何代码或测试读取它 | `[未证实]` |
| [`.kimi-plugin/plugin.json`](../../.kimi-plugin/plugin.json) | Kimi | 机器声明，**未被证实** | 无已知破坏；Kimi 不在 CLI 目标集合内 | `[未证实]` |
| [`gemini-extension.json`](../../gemini-extension.json) | Gemini CLI | **未证实** | 无已知破坏；架构注册表自标 `evidenceStatus: pending` | `[未证实]` |

### 这张表为什么重要

六个入口里只有 **两个**被证明确实会被客户端读取。另外四个是**声明性存在**：仓库里有、仓库自测通过，但没有任何证据表明有客户端消费它们。

把它们写成「支持的入口」会制造虚假能力声明。本仓库的定位是 evidence-backed——**入口存在 ≠ 客户端会读**，两者必须分开陈述。

`.cursor-plugin/`、`.kimi-plugin/`、`gemini-extension.json` 三者在 [`config/repository-architecture.json`](../../config/repository-architecture.json) 中均标为 `evidenceStatus: "pending"`（`.claude-plugin` 标为 `legacy`，`.agents` 标为 `manifest`），与上表一致。

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

验证方式：`find .agents -type f` 在本仓库只返回一个文件，即 `.agents/plugins/marketplace.json`。

## 与 canonical 层的接缝

分发入口不产生权威内容，只做翻译：

- `config/team-manifest.json` → `bin/installer/` → 各 harness 的原生产物
- `config/cli-adapters.json` → [`bin/installer/catalog.mjs`](../../bin/installer/catalog.mjs) → 19 个 CLI 目标（**恰好 19 个**，三处硬校验，见 [Adapter 注册机制](./adapter-registration.md)）
- 五个主力框架额外有 `config/harness-adapters/<id>.json` + `bin/adapters/<id>.mjs`

具体落盘位置与接线行为见 [主力框架接入手册](../guides/harness-adapters.md)；逐框架的调研结论见 [各 Coding Agent 的装配机制](../researchs/coding-agent-assembly.md)。

## 已知矛盾（记录，未修改）

以下两处不一致**已确认存在**，但本文**不修改**它们——它们分别归属 `config/` 与 `docs/architecture/`，改动需要单独的决策：

1. **名不副实**：[`docs/architecture/repository-architecture.md`](./repository-architecture.md) 第 66 行把 `.agents/` 描述为 "shared repo marketplace"，但该文件实际**只声明 Codex 一个插件**（见上表）。称之为 "shared" 与内容不符。
2. **role / module 错配**：[`config/repository-architecture.json`](../../config/repository-architecture.json) 给 `.codex` 的 `role` 是 `public-navigation`，`module` 是 `distribution-adapters`。role 说它是给公众看的导航，module 说它是分发适配器——两者语义冲突；`.codex/INDEX.md` 实为**仅人类**的安装指引（`[实测]`），更接近导航而非适配器。

## 返回

- [文档索引](../README.md)
- [仓库架构地图](./repository-architecture.md)
- [Adapter 注册机制](./adapter-registration.md)
