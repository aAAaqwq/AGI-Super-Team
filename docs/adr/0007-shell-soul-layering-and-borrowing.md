# ADR-0007: 壳与魂的分层归属，以及从三家 harness 汲取什么

- Status: Proposed
- Date: 2026-09-16

> **与既有文档的关系（重要）**：本文**不再论证"要不要以 DSH 为基座"** —— 那个决定已由
> [实施计划：DSH primary adapter](../plans/dsh-primary-adapter.md) 与
> [DSH 装配调研](../researchs/adapter-dsh.md) 记录，且已完成零成本验证
> （`$DSH_HOME` 隔离、patch 层位置、`customSkillDirs` 运行时可达等）。
>
> **本 ADR 只回答三个尚未被记录的问题**：
> ① 哪些部件属于「壳」（借）、哪些属于「魂」（自建），各自在 DDD 的哪一层；
> ② 从 Claude Code / Hermes / DSH 三家分别汲取什么；
> ③ 「魂」的完整清单（含此前遗漏的「自进化」）。

## Context

本仓库当前是**内容层 + 分发层**：一份 harness-agnostic 的契约（`config/team-manifest.json`、`*-specialists.json`、`agent-hierarchy.json`）编译成 18 家 harness 的原生格式（`bin/adapters/*.mjs`）。它提供的是 **agent 团队的组织与路由**，不提供执行。

我们把这个项目的差异化能力称为**「魂」**，共七块：

| # | 魂 | 现状 |
|---|---|---|
| ① | 组织结构 + 角色人格（14 C-suite + 92 叶子） | ✅ 已有 |
| ② | 路由分级 L0–L3 | ✅ 已有 |
| ③ | 责任与证据文化（委派契约 / 不能自证） | ✅ 已有 |
| ④ | 人类闸门（不可逆动作需人批） | ✅ 已有 |
| ⑤ | 自研 skills → 自己的 skills 市场 | ❌ 全新 |
| ⑥ | 人性化驾驶舱前端 | ❌ 全新 |
| ⑦ | **自进化** | ❌ 全新 |

> **⑦ 是补记**：本 ADR 初稿只列了六块，漏了「自进化」—— 而它恰是原始构想里的核心诉求之一
> （"拆解→分派→归并→解决→总结→**自进化**"）。查证结论见下文「三家汲取」一节：
> **能借的是治理，借不到的是适应度。**

**问题**：①②③④ 目前编译到**别人的壳**里，因此

- 路由/复核/闸门只能是**软约束**（各家 harness 能力不同，详见 `docs/guides/routing-and-enforcement.md` 的硬度矩阵）；
- ⑤⑥ **在结构上不可达** —— 我们没有 registry，也没有 UI 入口。

自建完整 harness（模型网关 / 工具运行时 / 控制循环 / 会话状态）被排除：那是重造轮子，且与成熟基座正面竞争。

## Decision

**以 `dsh`（DeepSeek Harness）为基座，把「魂」做成一个 bundle 插件包，不 fork。**

壳借、魂自建、边界如下的分工：

| 部件 | 归属 | 依据 |
|---|---|---|
| 模型网关 / 工具运行时 / 控制循环 / 会话状态 | **借 dsh** | 原生提供，且可替换 |
| 调度（cron / 队列） | **借能力 + 自建调度器** | dsh **无 cron**；用外部 launchd 调 `dsh --profile headless` |
| ① 组织结构 | **魂**（插件） | `ctx.subagents` + Agent Presets + `persona` + `toolFilter` |
| ② 路由分级 | **魂**（插件） | `tools.guard()` + `tools/pre-execute` |
| ③ 责任与证据 | **魂**（prompt/协议） | 无需原生机制 |
| ④ 人类闸门 | **魂**（root 层） | `ctx.approval`，fail-closed |
| ⑤ skills 市场 | **魂**（插件） | 注册远程 `SkillProvider` |
| ⑥ 驾驶舱 | **魂**（插件） | 占用 `main` 全局槽位；**已有同类先例** `packages/experimental/client-ui-agent-team`（roster + task board，就是插件做的）|
| 18 家分发 | **保留为兼容层** | 既有资产，不放弃 |

### 必须自建的三样

1. **路由策略插件** —— 关键事实：**dsh 没有"拦截子代理派发"的 hook**（`subagent/start` / `subagent/end` 都是 `@mode emit`：观察-only、异常被吞、返回值永不被读、发射发生在 run 已发布之后）。**必须拦截委派工具本身**。
   两层都用上：
   - `tools/pre-execute`（waterfall，16 个可短路事件之一）—— 可 `allow` / `deny` / `cancel` / `ask`，可读 `exec.agent`。**可扩展但可被 `{prepend:true}` 覆盖。**
   - **`ctx.tools.guard()` —— 单调的晚闸**：在整条 waterfall 之后运行，只返回 `string | undefined`（拒绝或弃权），**没有任何 listener 能翻案**（有测试专门验证：注册 `{prepend:true}` 的 allow，guard 仍然赢）。**这才是"硬约束"的真正落点。**
   - 需匹配的工具名（已核实）：`subagent`、`subagent_fork`（来自 `@deepseek-ai/dsh-tool-subagent`，名字可被 overlay 改）、`spawn_teammate`（agent-team）。仓库里**不存在** `spawn_agent` / `task` / `delegate` 这些名字。
2. **角色组合** —— dsh 的子代理**强制继承父 preset**（`packages/subagent/subagent/src/child-agent.ts:205`）。92 个叶子若要各自独立的工具集与提示词，有两条路：
   - **每次委带 `toolFilter`**（`SubagentStartRequest.toolFilter`），或**按角色挂多个 `tool-subagent` 实例**、每个实例一份 `config.toolFilter`；
   - 或自定义 `SubagentProvider`，在同步 `setup` 窗口里把子代理绑到角色 preset。
   ⚠️ **一个必须知道的限制**：`ctx.tools.restrict()` 过滤的是**继承来的工具面**，且**子代理拿到的是挂在 preset standing mount 下的新扁平 scope（不是父 agent 的 scope）**。所以**"只对某一个角色隐藏某个工具"无法靠单次 restrict 表达** —— 必须靠"每角色一个 mount/preset"或"在 `agent/created` 里往 `agent.ctx` 注册工具"。这是 ① 的主要实现成本。
3. **调度器** —— dsh 无 cron、无跨 session 持久队列。用本仓库既有的 launchd 模式调 `dsh --profile headless "<task>" --json --session-id <id>`。

## 分层归属：壳与魂在 DDD 的哪一层

```
┌──────────────────────────────────────────────────────────────┐
│ ① 接口层 / Interface                                          │
│    驾驶舱 UI · CLI · 通知 · webhook                            │
│    载体 = 壳（DSH 的 slot 前端 / CLI）                         │
│    信息架构 = 魂（"看什么、怎么组织"只对这套组织有意义）          │
├──────────────────────────────────────────────────────────────┤
│ ② 应用层 / Application                                        │
│    任务队列 · 调度器 · 会话生命周期 · 团队组建 · 归档            │
│    机制 = 壳（队列、job、进程）· 策略 = 魂（判级、选队、产物归属）│
│    ★ 壳与魂咬合最紧的一层 ★                                    │
├──────────────────────────────────────────────────────────────┤
│ ③ 领域层 / Domain   ★★★ 魂唯一纯粹的所在 ★★★                 │
│    ① 组织结构 ② 路由分级 ③ 责任与证据 ④ 人类闸门(策略) ⑦ 自进化 │
├──────────────────────────────────────────────────────────────┤
│ ④ 基础设施层 / Infrastructure                                 │
│    模型网关 · 工具运行时 · 沙箱 · 持久化 · 后台执行 · 拦截 · 插件 │
│    几乎纯壳                                                    │
└──────────────────────────────────────────────────────────────┘
```

**判据（一句话，可替代后面所有"该借还是该建"的讨论）**：

> **凡是「换个团队也成立」的 → 壳；凡是「只对这套组织成立」的 → 魂。**

验一下：

| 东西 | 换个团队还成立吗 | 判定 |
|---|---|---|
| 模型网关 / 工具运行时 / 沙箱 | ✅ | 壳 |
| 后台任务注册表（`ctx.jobs`） | ✅ | 壳 |
| slot 前端 / 空 `main` 槽 | ✅ | 壳 |
| **L0–L3 分级** | ❌ 只对 14+92 的组织成立 | **魂** |
| **"叶子不得派发"** | ❌ | **魂** |
| **"被审方不能自证"** | ❌ | **魂** |
| **驾驶舱该显示哪几栏** | ❌ | **魂** |

### 一个容易归错位的例子：持续后台 agent 执行

它**不是魂**，是**魂的载体**（基础设施层）。拆开看就清楚：

| 诉求 | 归属 | 机制 |
|---|---|---|
| 任务能后台跑、不占主进程 | **壳** | DSH `ctx.jobs`（插件可定义自己的 job kind）+ OS launchd 调 headless |
| **什么任务、何时、什么条件跑** | **魂** | 调度策略（领域层）—— DSH 无 cron，必须自建 |
| 跑完归到哪、谁负责、失败怎么办 | **魂** | 归档与治理规则（领域层） |

> **结论：别写后台执行引擎（借），但一定要写调度策略（建）。**
> 前者是轮子，后者才是"团队能持续运转"这句话的全部内容。

## 三家汲取：从 Claude Code / Hermes / DSH 各取什么

| 从谁 | 取什么 | 具体 |
|---|---|---|
| **Claude Code** | **循环的默认值** | fail-closed（后台子代理无法弹提示时，**仍然跑 hook；无 hook 给决策就拒绝**）· 拦截先于权限（`PreToolUse` 在任何权限模式之前，`deny` 连 `--dangerously-skip-permissions` 都挡）· 权限分层 allow/ask/deny · 子代理独立上下文 + 深度 + 工具限制 · **skills 懒加载**（name+description 常驻、正文按需 —— 833 个 skill 不炸上下文全靠它）· compaction · plan mode |
| **Hermes** | **自动改写的治理** | 门户 staging（高风险写入落 `pending/`，人审后 commit）· **双层回滚**（整树快照 + 单条 mutation 的 JSONL 账本 + 内容寻址 blob）· fail closed（快照写不进去就什么都不改）· provenance ContextVar（`foreground`/`background_review`/`refine_review`）· read-before-write 强制 · 永不自动删除（最坏 archive）· pin + 引用豁免 · **cron 里禁用学习闭环**（官方 `skip_background_review=True`）· benchmark 是 gate 不是 fitness |
| **DSH** | **壳本身** | 前端 slot 体系（`main` 是官方保留、当前为空的整页槽）· 16 个可短路 waterfall + `ctx.tools.guard()`（单调、不可翻案）· everything-is-a-plugin（连 agent loop 可换）· 内置 CC/Codex `hooks.json` 桥（既有 hook 资产不废）· `customSkillDirs`（自家 skills 目录即市场） |

### ⚠️ 关于「自进化」：能借治理，借不到适应度

查证结论（对 `NousResearch/hermes-agent` 源码 + 4 个相关 PR 的核实）：

1. **Hermes 官方没有叫 "Dreaming" 的自进化机制** —— 全仓零命中，4 个相关 PR **全部未合并**。
2. **Hermes 确有官方学习闭环，但它不是"进化"** —— 触发是**轮次计数**（每 10 turn / 15 iteration），输入是会话快照，**只改记忆与 skill 两个 markdown store**，且**没有任何适应度函数**。其 prompt 明写 *"Be ACTIVE — a pass that does nothing is a missed learning opportunity"* —— 这是**在催促产出改动**，不是**在验证改动有效**。**更准确的名字是 `self-rewriting`。**
3. Nous 自己承认这个洞：其 skill 原文 *"If you don't have a scorer, stop and define one first — that's the hard part."*
4. 其独立仓库 `hermes-agent-self-evolution`（DSPy+GEPA）**有** fitness/gate/PR 流程，但与 `hermes-agent` **无集成**；且**连它真正传给 GEPA 的 fitness 也是"关键词重合率"这种粗糙代理**。

> **所以 ⑦ 自进化的实现原则**：
> **借 Hermes 的「治理」（staging / 双层回滚 / provenance / 窄边界 / 只提议不落盘），
> 但「适应度函数」必须自己造 —— 而只在有 oracle 的领域做（当前只有量化）。**
> 没有 oracle 的"自进化"就是自我感觉良好机 —— 这一条本项目已在量化上实证过。

## Consequences

**得到**

- ⑤⑥ 变得可达：注册远程 `SkillProvider` 即得市场入口；占用官方**当前为空**的 `main` 整页槽位即得驾驶舱。
- ①②③④ 从**软约束**升级为**可强制**（`guard` / `pre-execute` 是执行期拦截，不是提示词）。
- 白嫖网关、工具、循环、会话、headless、Python/TS SDK、`subscribeSessionTree()`（按 lineage 订阅整棵组织树 —— 正好是驾驶舱要的数据）。
- 分发面扩大而非收窄：dsh 是**新增**的一家壳，18 家兼容层保留。

**放弃 / 承担**

- **跟 dsh 上游**。当前 `0.1.6-alpha.1`，README 明确警告 *"THERE WILL BE COMPATIBILITY-BREAKING CHANGES"*。这是换了一种版本税，不是消除它。
- **路由不是安全边界**。dsh 官方在 `2026-07-12-subagent-persona-tool-filter-and-depth.md` 专门写了 "**Visibility is not authority**"：`toolFilter` 只改变子代理的工具视图，**不构成授权格**，挡不住同进程内另一个 Cordis context 直接调服务。**不得把 L0–L3 当作安全机制对外表述。**
- **没有插件 API 版本，也没有强制的 dsh 版本约束**。全仓无 `apiVersion` 字段；`engines` 只出现在 workspace 根（且是 `private`），**没有任何已发布的 `@deepseek-ai/dsh-*` 包声明 `engines`**；`peerDependencies` 是 workspace 协议、发布时重写成 caret，而 **npm 对未满足的 peer 只 warning、不失败**。
  → **插件与 dsh 的兼容性没有任何机器可检的保证，破坏只能靠我们自己发现。** 我们的 bundle 需要一个自检入口（启动时验关键 seam 是否存在），不能等用户报错。
- **④ 的限制其实与我们的设计相容**（不是风险，但必须写进实现约定）：dsh 让子代理**不能自己问人**，其 ask 被确定性拒绝、**不是上抛**。因此"需要人批准的动作"必须由子代理**显式返回给 root**，由 root 触发审批。**这条要作为编排协议的一部分写死在角色契约里**，否则子代理会在需要批准时直接失败。
- **skills 市场无签名/审计层**。dsh 全仓无签名验证、无安装审计、无 allowlist；`dsh plugin add` 就是**逐字的 pnpm 转发器**（`apps/cli/src/plugin.ts:134` 就一行 `spawnSync('pnpm', ...)`），没有 registry API 调用、没有索引拉取、没有签名检查。官方文档自己写明：安装外部插件 = **"permission to execute the package's code on your machine at install time, outside any sandbox the agent runs under"**（`publish.md`）；`SAFETY.md` 也称本项目 *"has not undergone a security audit and must not be treated as secure or production-ready"*。
  注意：沙箱只约束**子进程 argv**（`ctx.sandbox.confine`），**不覆盖插件自身的进程内 JS**。要做可信市场，只能 fork 改 host loader ——**而它的插件面里没有可挂的 seam**。
- **dsh 侧文档有缺口**：`docs/glossary.md` 与 `docs/architecture.md` 里 **"skill" 出现 0 次** —— 说明 skill 子系统虽然是一等能力，但未被纳入总体架构叙述。这意味着**上游对它的稳定性承诺更弱**，自建时要有心理准备。
- **⚠️ ⑥ 有一个未证实的前提**：dsh 的 client roster 是**组合决定**（写在 `cordis.patch.yml` 里），不是"包属性"——官方 note 原话：*"which plugins compose into a deployment is a composition decision, not a package property… discovery-by-scan cannot make that call."*
  **目前没有找到任何文档证明"用户 npm 装一个第三方包就能进 web profile 的 client roster"**。这直接影响"我们发一个 bundle，用户装上就有驾驶舱"这件事能否成立。**这是 ⑥ 的 Step 1 必须先验证的事**（用一个最小空面板插件，走完整安装路径，看它是否出现在 boot graph 里）。
- **⑥ 的样式受限**：`docs/web-styling.md` **明令禁止 Tailwind 与组件库**，主题 token（`--dsw-*`）归 `ui-theme` 所有，扩展只能用语义 token（`--dsw-alias-*`），且**没有为第三方提供主题覆盖层**。做"人性化驾驶舱"要在这些约束内做设计。

**未来的 fork 触发条件**（现在不做；真要做时面很小）

| 触发条件 | 最小 fork 面 |
|---|---|
| 叶子必须**自己**向人提问（而非上抛 root） | `packages/subagent/` 约 6 个文件，不碰 agent loop、不碰 core |
| 叶子必须有**完全独立 preset** | 同上 |
| skills 市场需要**签名/审计** | host loader —— dsh 无此 seam，代价最高 |

## Alternatives considered

| 方案 | 否决理由 |
|---|---|
| **A. 继续寄生（现状）** | ⑤⑥ 在结构上不可达；①②③④ 永远只能是软约束。不是"不够好"，是**有天花板** |
| **B. fork dsh 做发行版** | 当前无必须 fork 的需求；fork 会把"跟上游"变成"维护一个分叉"。**保留为未来选项**（触发条件见上） |
| **D. 自研完整 harness** | 重造网关/工具/循环/会话；与成熟基座正面竞争。违反"不造轮子" |

## Follow-ups

1. 产出 bundle 骨架（`package.json` 的 `dsh.bundle.patch` + `cordis.patch.yml`），先用 `dsh --profile <demo> --dump-config` 验证层能生效，不写业务。
2. 写**路由策略插件**（`tools.guard()` 版），用现有 `agent-hierarchy.json` 的 `subagents` 白名单作为数据源 —— 契约在插件里被真正执行。
3. 写**驾驶舱插件**（`sidebar.panellist` + `main` 两处注册），第一版只显示"当前有哪些 session / 谁在跑"，复用 `useSessions`。
4. 调度器：把现有 launchd 模式接上 `dsh --profile headless`。**三个已核实的可用面**：
   - `dsh --profile headless "<task>"` — 一次性跑完打印结果退出，**不开端口、无交互追问**；`--json` 给 NDJSON 事件流（`session` / `status` / `text` / `tool_call` / `tool_result` / `final`），退出码 `0`=完成 `1`=中止；`--session-id <id>` 可续用已持久化的 session。
   - `dsh --profile sdk` — stdio JSON-RPC；`dsh --profile acp` — 标准 Agent Client Protocol（自动化专用）。
   - Python SDK：`pip install deepseek-harness-sdk`（**自带 native dsh 可执行文件，不需要系统 Node**）。
   ⚠️ **坑（必须写进调度器设计）**：`final_response` 是"活动区间内最后一段已提交的 root assistant 文本"，**与你的 prompt 没有因果绑定**（官方 README 原话）。**所以调度器不能盲信它作为"这次任务的结果"** —— 要配合 `--json` 的事件流或让任务显式落盘产物来判定成功。
   ⚠️ 另注：`/api` 是**浏览器专用**（launch token → 签名 cookie），**明确拒绝 bearer token**，`--host 0.0.0.0` 被刻意禁用。**不要试图用 HTTP 驱动它。**
5. ⑤ 市场：**先走 `customSkillDirs`（配置字段，把 dsh 指向我们自己的 skills 树）验证"自家 skills 目录即市场"这条路**，成本最低；`SkillProvider` 接口的 JSDoc 明确把 "a remote registry" 列为设计用途，但那要自己写 provider。签名/审计层 dsh 无 seam —— **先不做，并在产品表述上明确"市场内容来自可信来源"的边界**。

## 证据来源

两路只读调查（`git clone --depth 1` 到 `/tmp`，未修改任何内容）：
- 编排/强制面：`packages/subagent/`、`packages/preset/agent-presets/`、`packages/core/tools/`、`packages/interaction/user-approval/`、`packages/jobs/`、`packages/schedule/`、`docs/subsystems/*.md`、`docs/cookbook/extension-cookbook.md`
- 产品/体验面：`packages/skill/`、`packages/client/ui-layout/`、`packages/client/ui-slots/`、`apps/web/`、`packages/bundle/headless/`、`python/sdk/`、`docs/user/develop/basic/publish.md`

关键反证（**不得忽略**）：
- dsh **无** cron 解析器、**无**插件 registry/marketplace、**无**跨 session 持久任务队列、**无** per-agent 授权格。
- dsh 的 skill 发现**不支持**递归 `**/SKILL.md`。
