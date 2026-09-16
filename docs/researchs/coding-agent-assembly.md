# 各 Coding Agent 的装配机制调研

记录 AGI Super Team 如何装配到六个主力 coding agent，以及每个框架**实际读取**的目录约定。

## 证据等级

本文每条结论都标注来源，未标注的推断不作为实现依据：

- `[实测]` — 在本仓库上跑过真实客户端命令并观察到结果
- `[官方]` — 厂商官方文档明确记载
- `[社区]` — 仅有第三方来源，**需实测确认后才能实现**

## 更正记录

本文第一版有三处错误，已修正：

| 原结论 | 实际情况 | 依据 |
|---|---|---|
| DSH 无插件机制 | **DSH 有完整插件系统**（`everything is a plugin`，基于 Cordis） | `[官方]` |
| Kimi 支持情况未知 | **`.kimi-plugin/plugin.json` 正是 Kimi 官方约定** | `[官方]` |
| OpenClaw 无插件市场 | **OpenClaw 有完整插件系统**（ClawHub / npm / git / 本地） | `[官方]` |

结论：**六个框架全部都有插件机制**，此前"只有 Codex 有"的判断是错的。

## 核心结论：统一路径存在

### 1. SKILL.md 是跨工具开放标准

`SKILL.md` 遵循 **Agent Skills 开放标准**（agentskills.io），被 Claude Code、Codex、Cursor、Copilot、Gemini CLI、DSH、Kimi、Hermes 等共同实现。`[官方]`

> Claude Code 官方文档："Claude Code skills follow the Agent Skills open standard, which works across multiple AI tools."

**这意味着 canonical Skills 的内容层天然可移植**——不需要为每个框架改写。

### 2. `~/.agents/skills/` 是事实上的跨工具汇聚点

| 位置 | 读取它的工具 | 依据 |
|---|---|---|
| `~/.agents/skills/` | **Codex、DSH、Kimi**（+ Augment） | `[官方]` |
| `.agents/skills/`（项目级） | Codex、DSH | `[官方]` |
| `~/.claude/skills/` | Claude Code（+ Augment 兼容读取） | `[官方]` |
| `~/.hermes/skills/` | Hermes | `[官方]` |

DSH 文档直接称 `~/.agents/skills/` 为「**行业标准位置**」。Kimi 文档亦称其与 Claude Code 共享同一 skill 根。

### 3. 仓库级 marketplace 也统一了

**`.agents/plugins/marketplace.json`** 是 Codex 官方推荐的仓库级 marketplace，且明确是**多 harness 共享**位置。`[官方]`

```json
{
  "name": "agi-super-team",
  "plugins": [
    { "name": "agi-super-team-codex",
      "source": { "source": "local", "path": "./plugins/agi-super-team-codex" } }
  ]
}
```

`source.path` 指向仓库内插件目录 → **插件本体可集中放在 `plugins/` 下**。`[实测]` 现有配置已验证可解析。

## 六框架装配矩阵

| 框架 | 插件机制 | 权威目录 / 命令 | 技能根 | 证据 |
|---|---|---|---|---|
| **Codex** | ✅ marketplace | `.agents/plugins/marketplace.json`<br>`codex plugin marketplace add` | `~/.agents/skills/` | `[实测]` |
| **Claude Code** | ✅ marketplace | `.claude-plugin/marketplace.json`（**强制**）<br>`claude plugin validate .` | `~/.claude/skills/` | `[官方]` |
| **OpenClaw** | ✅ plugins | `openclaw plugins install <pkg>`<br>`openclaw.plugin.json` 清单 | 受管 skill 根 | `[官方]` |
| **Hermes** | ✅ plugins | `hermes plugins install owner/repo`<br>根 `plugin.json` | `~/.hermes/skills/` | `[官方]` |
| **Kimi** | ✅ plugins | `.kimi-plugin/plugin.json` 或 `kimi.plugin.json`<br>`kimi plugin` 命令 | `~/.agents/skills/`、`~/.kimi-code/skills/` | `[官方]` |
| **DSH** | ✅ plugins | `dsh plugin --profile <p> add "github:owner/repo#main"` | `~/.dsh/skills/`、`~/.agents/skills/` | `[官方]` |

## 逐框架细节

### Codex

- CLI：`codex plugin marketplace add owner/repo`、`codex plugin list`、`codex plugin add <name>@<marketplace>` `[官方]`
- 仓库级 marketplace：`$REPO_ROOT/.agents/plugins/marketplace.json` `[官方]`
- `.codex-plugin/plugin.json` 是**兼容回退**，非必需 `[官方]`
- 缓存：`~/.codex/plugins/cache/$MARKETPLACE/$PLUGIN/$VERSION/` `[实测]`

`[实测]`（codex-cli 0.153.4）：

```
$ codex plugin marketplace add <repo>
Added marketplace `agi-super-team`
$ codex plugin add agi-super-team-codex@agi-super-team
Added plugin `agi-super-team-codex` from marketplace `agi-super-team`.
Installed plugin root: ~/.codex/plugins/cache/agi-super-team/agi-super-team-codex/1.6.0
```

**实测附带确认**：移除根级 `.codex-plugin/` 后输出逐字相同 → 该目录对插件发现无作用，本仓库已删除。

### Claude Code

- **marketplace 必须在仓库根 `.claude-plugin/marketplace.json`**，加载器强制此约定 `[官方]`
- `metadata.pluginRoot`（v2.1.239+）可让插件本体收拢到 `plugins/` `[官方]`
- `source` 路径相对 marketplace 根解析，**不允许 `../`** `[官方]`
- 本地校验：`claude plugin validate .` `[官方]`

**结论**：`.claude-plugin/` 目录名不可动，但 `pluginRoot` 提供了集中插件本体的官方途径。

### OpenClaw

- **有完整插件系统**：`openclaw plugins install <pkg>`，源支持 ClawHub / npm / git / 本地目录 / 压缩包 `[官方]`
- 原生插件需 `openclaw.plugin.json`（含内联 JSON Schema）`[社区]`
- 兼容其它生态的 bundle（自带 manifest 格式），OpenClaw **自动探测** `[社区]`
- 管理：`openclaw plugins list [--enabled] [--verbose]`、`openclaw plugins inspect <name>` `[官方]`
- 本仓库当前走安装器路径（`--tool openclaw --install --connect`），未使用插件形态

### Hermes

- **可移植插件格式（Agent Plugins v1.0.0）**：包根放 `plugin.json` + `skills/` + 可选 `mcp.json` `[官方]`
- 安装：`hermes plugins install owner/repo --no-enable` → `hermes plugins enable <name>` `[官方]`
- **安装后默认禁用**，必须显式 enable `[官方]`
- 每次 install/update 会跑**静态安全扫描**（凭据外泄、反弹 shell、破坏性命令等）`[官方]`
- 技能根：`~/.hermes/skills/`；插件：`~/.hermes/plugins/` `[官方]`

**注意**：Hermes 要求 `plugin.json` 在**插件包根目录**，与本仓库现有的 `.codex-plugin/plugin.json` 布局不同。需新增 Hermes 形态的插件包。

### Kimi

- **manifest 两个合法位置**：`/kimi.plugin.json` 或 `/.kimi-plugin/plugin.json`；**两者同时存在时 `kimi.plugin.json` 优先** `[官方]`
- **这正是本仓库已有 `.kimi-plugin/plugin.json` 的原因** —— 它是官方约定，不是自造 `[官方]`
- 安装位置：`~/.kimi/plugins/`（每插件一个子目录）`[官方]`
- 命令：`kimi plugin` 管理插件 `[官方]`
- 数据根：`$KIMI_CODE_HOME`（默认 `~/.kimi-code`），含 `skills/`、`plugins/installed.json` `[官方]`
- 技能根包括 `~/.agents/skills/`（与 Codex 共享）`[官方]`
- 插件可携带 `skills/`（同 SKILL.md 格式）与 `agents/`（subagent）`[官方]`

### DeepSeek Harness (DSH)

- **插件系统是核心架构**：「everything is a plugin」，基于 Cordis 内核 `[官方]`
- 安装：`dsh plugin --profile <profile> add "github:owner/repo#main"` `[官方]`
- 插件以 `apply(ctx)` 注册能力，卸载时自动清理（可逆） `[官方]`
- **技能根（按 rank，数字越小优先级越高）** `[官方]`：

  | Rank | 路径 |
  |---|---|
  | 100 | `<项目根>/.dsh/skills` |
  | 200 | `<项目根>/.agents/skills` |
  | 300 | `Config.customSkillDirs` |
  | 400 | `~/.dsh/skills`（`$DSH_HOME`） |
  | 500 | `~/.agents/skills` |

- **格式**：`<name>/SKILL.md` 或 `<name>.md`，**只扫一层，不递归** `[官方]`
- **frontmatter 必需** `name`（kebab-case）+ `description`；非法则**静默丢弃** `[官方]`
- 目录型技能（含 `references/`、`scripts/`）必须声明 `resourceBase`，否则相对路径断裂 `[社区]`

## 统一策略

三层结论：

| 层面 | 能否统一 | 做法 |
|---|---|---|
| **技能内容** | ✅ 已统一 | SKILL.md 遵循 agentskills.io 开放标准，一份内容全工具可用 |
| **技能落盘位置** | ⚠️ 部分统一 | `~/.agents/skills/` 覆盖 Codex + DSH + Kimi；Claude Code / Hermes 各有其根 |
| **插件/市场位置** | ⚠️ 部分统一 | `.agents/plugins/marketplace.json` 为共享入口；`.claude-plugin/` 与 `.kimi-plugin/` 是客户端强制约定 |

**推荐形态**：

1. **canonical Skills 保持单份**，走开放标准格式 → 内容层天然跨工具
2. **插件包本体集中放 `plugins/<harness>/`**，由 `.agents/plugins/marketplace.json` 统一索引
3. **只为客户端强制约定保留根级目录**：`.claude-plugin/`（Claude Code 强制）、`.kimi-plugin/`（Kimi 合法位置之一）
4. **OpenClaw / Hermes / DSH 优先用各自插件机制**，而非仅靠文件拷贝

**不能统一的**：各客户端的目录名是**写死的发现约定**（`.claude-plugin/`、`.kimi-plugin/`），改名即放弃该客户端。

## 当前差距

| 框架 | 当前状态 | 差距 |
|---|---|---|
| Codex | ✅ 插件可装 | — |
| Claude Code | ⚠️ 走安装器 | 可加 `pluginRoot` 集中插件 |
| OpenClaw | ⚠️ 走安装器 | 未封装为 OpenClaw 插件 |
| Hermes | ❌ 无 Hermes 形态包 | 需根 `plugin.json` 的插件包 |
| Kimi | ⚠️ 有 manifest | 未实测验证 Kimi 是否识别 |
| DSH | ❌ 无 adapter | 无适配器；且受 [Adapter 注册的 18 个硬约束](../architecture/adapter-registration.md) 限制 |

## 复现本文的实测

```bash
# Codex 装配（实测命令，已验证）
git archive HEAD | (mkdir -p /tmp/probe && tar -x -C /tmp/probe)
cd /tmp/probe
CODEX_HOME=/tmp/probe-home codex plugin marketplace add .
CODEX_HOME=/tmp/probe-home codex plugin list
CODEX_HOME=/tmp/probe-home codex plugin add agi-super-team-codex@agi-super-team
```

## 来源

- [Claude Code — Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Claude Code — Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [OpenAI — Package your plugin](https://developers.openai.com/codex/plugins/build)
- [OpenAI — Plugin management](https://developers.openai.com/codex/enterprise/plugin-management)
- [OpenClaw — Plugins](https://docs.openclaw.ai/tools/plugin)
- [Hermes — Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Hermes — Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/)
- [Kimi Code — Plugins](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html)
- [Kimi Code — Data locations](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/data-locations.html)
- [DeepSeek Harness — Skill System](https://deepseekdocs.com/en/docs/features/skills)
