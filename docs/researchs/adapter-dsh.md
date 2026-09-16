# DeepSeek Harness (DSH) 装配

> **状态**：**本仓库当前不支持 DSH**。本文记录 DSH 的实际机制与接入障碍，供评估使用。
>
> **核实记录**：2026-09-16 用 tavily 检索官方文档 + 本机实测（dsh `0.1.5-rc.1`）逐条核实。
> 证据等级：`[官方]`（附 URL）/ `[实测]`（附命令与输出）/ `[推定]` / `[无法证实]`。
> DSH 处于 **developer preview**，官方明示「THERE WILL BE COMPATIBILITY-BREAKING CHANGES」，
> 以下结论对版本敏感。

## 机制

DSH 是 DeepSeek 的 agent runtime / harness 层，架构原则是「**everything is a plugin**」，基于 Cordis 内核。`[官方]`
（<https://github.com/deepseek-ai/deepseek-harness>）

| 项目 | 值 | 证据 |
|---|---|---|
| 插件安装 | `dsh plugin --profile <profile> add "github:owner/repo#main"` | `[官方]` <https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/reference/README.md> |
| 启动 | `npx @deepseek-ai/dsh web` | `[官方]` 同上仓库 README |
| 生态主题 | 插件仓库应带 **`dsh-plugin`** GitHub topic 以便索引 | `[官方]` 仓库 README「Community and support」 |
| 插件形态 | TypeScript 模块，通过 `apply(ctx)` 注册可逆 effect，卸载自动清理 | `[官方]` <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cordis-tutorial/02-lifecycle-and-effects.md> |
| 插件分发形态 | npm 包，manifest 声明 `dsh.bundle` → `cordis.patch.yml` 层 | `[官方]` <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md> |

> **已修正**：本节原写「生态主题 `#dsh`」是**错误**的 —— 官方要求的是 `dsh-plugin` topic
> （`#dsh` 只是 awesome-list 的写法）。载荷来自第三方 awesome list 的描述不属官方。
>
> **已补充**：`dsh plugin --profile <name> <pnpm args>` 是**对 pnpm 的透传**
> （`add`/`remove`/`why`/`update` 等 verb 原样转发，pnpm 必须在 PATH）。
> GitHub 来源的插件在安装时跑 `prepare`，pnpm 默认阻止，需要在 profile 的
> `pnpm-workspace.yaml` 加 `allowBuilds` 白名单。`[官方]` 同上 CLI reference。

### 技能根（按 rank，数字越小优先级越高）

| Rank | 路径 | 作用域 |
|---|---|---|
| 100 | `<项目根>/.dsh/skills` | 项目 |
| 200 | `<项目根>/.agents/skills` | 项目 |
| 300 | `Config.customSkillDirs` | 自定义 |
| 400 | `<dshHome>/skills`（`$DSH_HOME`，默认 `~/.dsh/skills`） | 用户 |
| 500 | `<agentsHome>/skills`（`$DSH_AGENTS_HOME`，默认 `~/.agents/skills`） | 用户 |
| 600 | `Config.bundledSkillDir` / `$DSH_BUNDLED_SKILL_DIR`（配置了才有） | 内置 |

`[官方]` <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md>
与 <https://deepseekdocs.com/en/docs/features/skills>

**rank 表本身已核实为真。** 项目根 = 最近含 `.git` 的祖先目录，没有则用当前 cwd；用户 DSH 根会跳过其
`.system` 子目录。`[官方]`

> **已修正**：
> 1. 原表只有 5 行且标「`~/.dsh/skills`（`$DSH_HOME`）」——实际是 `<dshHome>/skills`，`$DSH_HOME`
>    被覆盖时路径随之变化（`DSH_HOME=/x` → `/x/skills`）；原写法会被误读成常量路径。
> 2. **漏了 rank 600**（`bundledSkillDir`）。`dsh-skill-badge` 正是注册在这个 rank 上的内置候选。
>
> **重要存疑（实测与官方文档不符）**：本机 `dsh` 是 `0.1.5-rc.1`，但该安装的主包里
> **grep 不到任何 skill 名称/路径解析常量**——rank 表与 `.dsh/skills`、`.agents/skills`、
> `customSkillDirs` 全部只存在于 `@deepseek-ai/dsh-skill-filesystem` 这个**插件包**的代码与
> README 里。`[实测]`
>
> ```bash
> $ grep -rl "customSkillDirs" ~/.local/lib/node_modules/@deepseek-ai/dsh/lib
> (无输出)
> $ grep -rl "customSkillDirs" ~/.local/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-skill-filesystem
> .../dsh-skill-filesystem/lib/index.js
> .../dsh-skill-filesystem/README.md
> ```
>
> 也就是说：**技能根是「skill-filesystem 插件」的机制，不是 dsh 主程序的机制。** 该插件由
> `@deepseek-ai/dsh-base` 的 bundle 层挂载（`[实测]` `dsh-base/cordis.patch.yml:274-277` 有
> `skill` / `skill-filesystem` / `skill-badge` / `tool-skill` 四行），**该 bundle 层可以被 profile
> 的 patch 覆盖或禁用**——例如 web-app bundle 就禁用了 host 层的 `agent-instructions` 行
> （`[官方]` <https://github.com/deepseek-ai/deepseek-harness/discussions/519>）。
> 结论：不能把 rank 表当成 dsh 的不变行为，必须验证**目标 profile 的最终 preset**
> （`dsh <profile> --dump-config`）。

### 技能格式

- `<name>/SKILL.md` 或平铺 `<name>.md`（均在扫描根的**顶层**）`[官方]` <https://deepseekdocs.com/en/docs/features/skills>
- **只扫一层，不递归**——埋到二级子目录不会被发现 `[官方]` 同上
- frontmatter 必需 `name`（kebab-case）+ `description`；可选 `whenToUse` / `metadata` /
  `disable-model-invocation` / `user-invocable` `[官方]` 同上
- 非法条目**静默丢弃**（fail-closed，只在本地 warn，模型目录拿不到逐条诊断）`[官方]` 同上
- 目录型技能（含 `references/`、`scripts/`）的 `resourceBase` **不是技能作者手写的** `[实测]`

> **已修正（重要）**：原文写「目录型技能必须声明 `resourceBase`，否则相对路径断裂」并把等级标为 `[社区]`。
> 核实结果：`resourceBase` 是 `SkillDefinition` 的**可选字段**，由**文件系统 provider 自动填充**
> ——`dsh-skill-filesystem` 在 `get()` / `list()` 里无条件下发
> `resourceBase: { kind: "directory", path: locator.directory }`。`[实测]`
>
> ```js
> // .../dsh-skill-filesystem/lib/index.js:126 与 605（get() 与 catalog 两条路径）
> resourceBase: { kind: "directory", path: locator.directory }
> ```
>
> 也就是说磁盘上的目录型技能**无需任何声明即可正确解析相对资源**；只有**编程式**
> `SkillRegistration`（不经文件系统 provider）才需要自己给 `resourceBase`
> （类型为 `{kind:'directory',path} | {kind:'url',url} | {kind:'opaque',description}`）。`[实测]`
> 依据：`@deepseek-ai/dsh-skill/lib/types/index.d.ts:26-35`。
> 原文该条实际引用的是第三方博客（bibigpt.co）的说法，**不适用于本仓库的落盘型技能**。

### 环境变量

| 变量 | 默认 | 作用范围 | 证据 |
|---|---|---|---|
| `DSH_HOME` | `~/.dsh` | **全 harness**：profile 根、settings、sessions、credentials、shell 快照 | `[官方]` <https://deepseekdocs.com/en/docs/features/skills> + <https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/reference/README.md> |
| `DSH_AGENTS_HOME` | `~/.agents` | **仅 `skill-filesystem` 插件**的 agentsHome 配置默认值 | `[实测]` 见下 |

> **已修正（重要）**：原文把两个变量并列成同一层机制。核实结果差异很大：
>
> 1. `DSH_HOME` 名字**确实存在**，但「默认 `~/.dsh`」这个默认值**不在环境变量层**——由
>    `@deepseek-ai/dsh-home-paths` 的 `resolveDshHome()` 实现，优先级
>    **显式配置 > `$DSH_HOME` > `~/.dsh`**（空白值视为未设置）。`[实测]`
>    `~/.local/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-home-paths/lib/index.js:11-15,65-80`
>    （常量 `DSH_HOME_ENV = "DSH_HOME"`、`DSH_HOME_DIR_NAME = ".dsh"`）
> 2. `DSH_AGENTS_HOME` 名字**确实存在**，但**只在 `@deepseek-ai/dsh-skill-filesystem`
>    这一个包内被引用**——它只是该插件 `agentsHome` 配置字段的默认值表达式
>    `$DSH_AGENTS_HOME or ~/.agents`，**不是跨 harness 的通用环境变量**。`[实测]`
>
>    ```bash
>    $ grep -rln "DSH_AGENTS_HOME" ~/.local/lib/node_modules/@deepseek-ai/dsh
>    .../dsh-skill-filesystem/README.md
>    .../dsh-skill-filesystem/README.zh.md
>    .../dsh-skill-filesystem/lib/index.js
>    .../dsh-skill-filesystem/lib/types/index.d.ts
>    # ← 只有这一个包，主包与 dsh-home-paths 均无
>    ```
>
>    **推论（直接影响本仓库）**：该变量是**插件配置值**，profile 的 `cordis.patch.yml`
>    可以用 `agentsHome:` 直接覆盖它。所以「DSH 读 `~/.agents`」不是环境契约，而是
>    **该 profile 恰好没覆盖这个字段**的部署默认值。
>
> 另有 `DSH_BUNDLED_SKILL_DIR`（bundled skill 根，rank 600）`[官方]` skills.md。
> 本机实测 `env | grep '^DSH'` 为**空**——`~/.dsh` 与 `~/.agents` 都是走代码默认值，
> 不是环境变量注入。`[实测]`

## Agent 机制 —— 接入 DSH 的主要难点

**DSH 没有「agent 定义文件」这一原生产物。** 角色的能力组合由 **agent preset** 承载，
人设由 **persona** 承载，工作区指令由 **AGENTS.md 指令链**承载——三者是**三个不同机制**。

`[官方]` <https://deepseekdocs.com/en/docs/features/persona>

| 机制 | 管什么 | 载体 |
|---|---|---|
| **Agent preset** | 该 agent 的完整能力组合（tools / prompt sections / projection units / skills） | 一个目录 + `agent.cordis.yml` |
| **Persona** | 该 agent 的人设 / system prompt 片段 | 一条可组合的 system-prompt 行（`@deepseek-ai/dsh-persona`） |
| **指令文件** | 工作区规则 | `AGENTS.md` 链（见下表） |

> **已修正（关键）**：原文写「DSH **没有独立于 Skill 的 agent 文件目录**，角色与指令通过
> **AGENTS.md 指令链**注入」——**前半句正确，后半句错误**。
>
> - 前半句成立：实测主包 grep `agents/` 类目录约定无命中；DSH 没有
>   `~/.dsh/agents/*.md` 这种**内建**的 agent 文件目录。`[实测]`
> - 后半句**错误**：能限制 agent 能力边界的是 **preset（`~/.dsh/.agent-presets/<id>/agent.cordis.yml`）**，
>   **不是 AGENTS.md**。AGENTS.md 只是**低权限的工作区参考文字**——官方原文明确：
>   「workspace instructions do not override system, developer, or direct user instructions」，
>   它是**建议性上下文**，不是可执行的能力/权限定义。`[官方]`
>   <https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/context/agent-instructions/README.md>
>   （另见第三方实测手册 <https://github.com/sandbaseai/deepseek-harness-handbook/blob/main/docs/en/agent-patterns/agents-md-scope.md>）
>
> **这实际上放宽了原文的悲观结论**：DSH 有比 AGENTS.md **更强**的角色载体（preset + persona），
> 只是**形态不同**——一个 preset 是一个目录加一份 `agent.cordis.yml`，而不是「每角色一个 `.md`」。

### AGENTS.md 指令链（已核实）

| 项目 | 值 | 证据 |
|---|---|---|
| 指令文件候选 | `AGENTS.md`、`CLAUDE.md` | `[官方]` agent-instructions README |
| 本地覆盖 | `AGENTS.local.md`、`CLAUDE.local.md`（叠加，在基础候选之后） | `[官方]` 同上 |
| 项目根标记 | `['.git']`（`projectRootMarkers`，可配置） | `[官方]` 同上 |
| 用户全局 | `$DSH_HOME/AGENTS.md`（**固定文件名**，不是 `AGENTS.md` 候选链） | `[官方]` 同上 |
| 加载顺序 | 用户全局 → 项目根 → 会话工作目录，**宽 → 专** | `[官方]` 同上 |
| 渲染预算 | `maxBytes` **必需**；`dsh-base` 下发 **65,536** 字节 | `[官方]` 同上 |
| 单文件上限 | `maxSourceBytes` 默认 **1,048,576**（1 MiB） | `[官方]` 同上 |
| 预算淘汰 | 先丢**整份较宽泛文件**，再截断最具体文件；渲染字节**绝不超 `maxBytes`** | `[官方]` 同上 |
| 超预算源码文件 | **整个忽略**（不是截断来源文件） | `[实测]` config.ts：`maxSourceBytes` 注释「larger files are ignored」 |

去重规则：**逐目录**按 trim 后内容比对，相同则折叠到最早候选（例如 `CLAUDE.md` 与同目录
`AGENTS.md` 内容一致时不重复注入）。`[官方]` 同上。

> **已修正**：原文的 `maxBytes` 行写「**必需**（典型部署 65536 字节）；单文件
> `maxSourceBytes` 默认 1 MiB」，并把它放在**指令链表内**。核实后：
> - `maxBytes` 是 **required 且无默认**（每个部署必须显式给），65536 是 **`dsh-base` 下发到
>   `agent-instructions` 行的值**，不是「典型部署」的经验值。`[官方]`
> - 是**先丢整份宽泛文件再截断**，不是简单截断——直接影响「全局 AGENTS.md 会不会被吃掉」。
> - 原文漏了**超预算的 source 文件会被整份忽略**这一条。

### Subagent

**核实结果：原文基本正确，但包名要写全。** `[官方]` <https://deepseekdocs.com/en/docs/features/subagent>

- 委派面是 `ctx.subagents` **能力缝**；模型面对的是两个独立插件：
  - **`tool-subagent`** —— 一次性（one-shot）委派，走 `ctx.subagents.start()`
  - **`tool-subagent-control`** —— 可续（continuable）子会话控制面：`send_message` /
    `interrupt_agent` / `list_agents`
- 两者在 `dsh-base` 的 bundle 层挂载。`[实测]` `dsh-base/cordis.patch.yml:328-363`
  有 `subagent` / `subagent-spawn-in-process` / `subagent-fork-in-process` /
  `tool-subagent-control` / `tool-subagent-control/list-agents` / `tool-subagent` 六行。

> **已修正**：原文只写「由 `tool-subagent` 插件提供」。实际是**两个**模型面对的工具包
> （`tool-subagent` + `tool-subagent-control`）加一个**服务包**（`dsh-subagent`，注册
> `ctx.subagents`）。对适配器的实际影响：DSH 的「subagent」**不是**一个可由配置声明的
> 角色定义，而是**运行时委派调用**——`persona`、`toolFilter`、`maxDepth`、`agentOptions`
> 都要在**调用时**由父 agent 传入（或由 preset 的 `tool-subagent` 行给默认值）。`[官方]` 同上。

### 为什么这构成障碍

现有四个 primary harness（Claude Code / Codex / OpenClaw / Hermes）的 Adapter 都按「**每个角色一个原生文件**」建模——Claude 写 `ast-ceo.md`、Codex 写 `ast-ceo.toml`。

DSH **不适用这个模型**：它没有内建的 agent 文件目录。角色的能力边界只能落在
`~/.dsh/.agent-presets/<id>/agent.cordis.yml`（preset），人设落在 `dsh-persona` 行，
工作区文字落在 AGENTS.md（**低权限、可被预算丢弃**）。这意味着接入 DSH 需要一条
**与现有四个 Adapter 不同的产物渲染路径**。

> **已修正**：原文此处写「角色只能作为 `AGENTS.md` 指令链的一部分注入」——见上文，
> 能力/角色语义应由 **preset** 承载，AGENTS.md 只是建议性上下文。
> 「需要不同的产物渲染路径」这个**结论仍然成立**，且工作量比原文估计的**更大**
> （要同时处理 preset 目录 + persona 行 + AGENTS.md 三种产物，而非只写一个 AGENTS.md）。

## 接入 DSH 需要的改动

详见 [DSH primary adapter 实施计划](../plans/dsh-primary-adapter.md)。摘要：

1. 新增 CLI 目标 → 同时改三处「恰好 18 个」硬约束
2. 实现 `bin/adapters/dsh.mjs`，导出 `ADAPTER_ID` / `renderAdapterArtifacts` / `buildConnectionSpec`
3. 加入 `priorityHarnesses`（硬编码于 `bin/installer/catalog.mjs`）
4. 解决 agent 装配模型差异（最主要工作量）

## 可以低成本拿到的部分

DSH 的 rank 500 技能根是 `<agentsHome>/skills`，默认 `~/.agents/skills/`，
**与 Codex 的落盘位置相同**。`[实测]` 本机 `~/.agents/skills/` 存在且有 **171** 个技能目录：

```bash
$ ls ~/.agents/skills | wc -l
     171
```

所以**技能层**理论上已经可用——用户跑一次 `--tool codex --install`，DSH 就能读到这些技能。
缺的是 **agent 层**与**官方接入路径**。

> **已修正（重要，削弱了这条的把握）**：
> 1. 原文写「rank 500」——**漏了「rank 500 排在 rank 100/200/300/400 之后，且同层同名的胜出
>    规则是 rank 优先」**；本地 Codex 技能会**输给**同名的项目级或 `~/.dsh/skills` 技能。
> 2. 原文写「DSH 的客户端行为**未实测**（本机未安装 `dsh`）」——**该前提已失效**：本机已装
>    `dsh 0.1.5-rc.1`（`~/.local/bin/dsh`，包 `@deepseek-ai/dsh`）。但**仍然没有跑过真实
>    session 去观察 catalog**，所以「DSH 会读到 `~/.agents/skills/`」依旧只是
>    「机制上成立」，**不是运行时证据**。`[推定]`
> 3. **不能把这当成稳的**：`agentsHome` 是 `skill-filesystem` 插件的一个**配置字段**
>    （见上文环境变量一节），profile 的 patch 层可以覆盖；且 `[官方]` skill-filesystem
>    README 明言「已发现、改名或删除的 skill 无需重启即可到达 agent」，但**目录型技能依赖
>    provider 正常挂载**。要断言「可用」，必须验证**最终 preset**（`dsh web --dump-config`）。
> 4. 原文说这是「行为巧合」——更准确的说法是**「共用的配置目录约定（`.agents/skills`）」**，
>    不是巧合。`[官方]` 多篇文档（含 deepseekdocs skills 页）确认这是**有意共享**的根。

## 待办

- [ ] **起一个真实 DSH session**，让它列出自己的 skill catalog 与 provider source，确认
      `~/.agents/skills/` 是否真被读取（机制已核实，**运行时仍未证实**；这是唯一能把这个
      结论从 `[推定]` 抬到 `[实测]` 的办法）
- [ ] 先 `dsh web --dump-config`（或 `dsh --profile <p> --dump-config`）确认目标 profile 的
      **最终 preset** 里 `skill-filesystem` 行仍然挂载、且 `agentsHome` 未被 patch 覆盖
- [x] ~~评估 `resourceBase` 对目录型技能的要求~~ —— **已核实为伪问题**：文件系统 provider
      自动填 `resourceBase`，落盘型技能无需任何声明（见「技能格式」一节）
- [ ] 评估 **agent preset（`agent.cordis.yml`）** 作为角色载体的可行性 —— 这是原文遗漏的
      第三条路，且比「塞进 AGENTS.md」语义强得多
- [ ] 按实施计划评估投入产出

## 未能核实的点

按「不允许把没查到的说成查到了」的要求，以下结论**没有找到官方出处**，明确标注：

| 说法 | 状态 | 说明 |
|---|---|---|
| DSH 会**在运行时**读取 `~/.agents/skills/` | `[无法证实]` | 机制链（provider 代码 + 官方文档）完整，但**未起 session 观察**。搜过 `deepseek-harness dsh skills roots rank`、`DSH_AGENTS_HOME`、官方 skills 页与 GitHub `docs/subsystems/skills.md`——都只到「provider 会扫这个根」这一步，没有可观测的运行时证据 |
| `maxBytes` 有官方推荐的「典型值」 | `[无法证实]` | 65536 是 `dsh-base` 硬编码给 `agent-instructions` 行的值（`[官方]` agent-instructions README 原文「`dsh-base` already includes it with a 65,536-byte budget」）。**不存在**「典型部署 65536」这种说法——是该 bundle 的选择，patch 层可改 |
| DSH 的 `desktop` profile | — | 与本任务无关，但核实中发现：`desktop` 是 Electron 独占保留名，CLI 拒绝 boot/dump/plugin（`[实测]` `lib/bin.js` `rejectElectronProfile`，报 `profile "desktop" is managed exclusively by the Electron application`） |
| DSH 本机版本 | `[实测]` | `dsh --version` → `0.1.5-rc.1`；包 `@deepseek-ai/dsh`，repository 为 `github.com/deepseek-ai/deepseek-harness`（monorepo，`directory: apps/cli`）。本机 `~/.dsh` 下**无** `cordis.yml` / `package.json`；这些在 `~/.dsh/profiles/rescue/` 内。实测有 `profiles/` + `sessions/` + `storages/` + `settings.yaml` + `.credentials.yaml` + `.anonymous-user-id`；`settings.yaml` 含 `agent-default-model: {provider: deepseek-official, model: deepseek-v4-flash, reasoningEffort: low}`。`~/.dsh/.agent-presets/` **尚未创建**（按需生成） |

## 相关文档

- [装配机制总览](./README.md)
- [DSH primary adapter 实施计划](../plans/dsh-primary-adapter.md)
- [DeepSeek Harness — Skill System](https://deepseekdocs.com/en/docs/features/skills)
