# OpenClaw 装配

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| 插件安装 | `openclaw plugins install <pkg>` | `[官方]` |
| 插件源 | ClawHub → npm → git → 本地目录 → 压缩包 | `[官方]` |
| 原生插件清单 | `openclaw.plugin.json`（含内联 JSON Schema，即使配置为空） | `[社区]` |
| 兼容 bundle | 其它生态的 manifest 格式由 OpenClaw **自动探测** | `[社区]` |
| 查看 | `openclaw plugins list [--enabled] [--verbose]` | `[官方]` |
| 检查 | `openclaw plugins inspect <name> [--json]` | `[官方]` |

### 配置与状态

| 项目 | 路径 | 覆盖变量 |
|---|---|---|
| 配置 | `~/.openclaw/openclaw.json` | `OPENCLAW_CONFIG_PATH` |
| State | `~/.openclaw` | `OPENCLAW_STATE_DIR` |
| Home | — | `OPENCLAW_HOME` |

配置里的关键节点：`models.providers`、`agents.defaults`、`agents.list` / `agents.entries`。`[官方]`

### Agent 机制

- 每个 agent 有独立 workspace 与 `agentDir`
- Agent 身份文件是 **`agent.md`**（Markdown），位于 `~/.openclaw/agents/<agent-id>/agent.md` `[社区]`
- workspace 里可放 `SOUL.md`、`AGENTS.md`、可选 `USER.md`
- 子 agent 通过 `agents.entries.<id>.subagents.allowAgents` 授权白名单 `[官方]`
- `sessions_spawn` 工具负责派生 `[官方]`

## 本仓库的装配方式

**走安装器，不用插件形态**：

```bash
npx -y agi-super-team@latest --tool openclaw --install --connect
```

- Agent 产物：`<当前配置目录>/agency-agents/agi-super-team/ast-*`
- 技能产物：`<当前配置目录>/skills/agi-super-team/<skill>`
- `--connect` 先 dry-run，再按 `id` 合并 `agents.list`，**保留非托管 Agent**，不创建 channel binding

### 配置目录解析顺序

显式 state → 显式配置文件所在目录 → 默认 state。

`--home` 表示 OS Home 基准，**不会静默覆盖** `OPENCLAW_HOME` / `OPENCLAW_STATE_DIR` / `OPENCLAW_CONFIG_PATH`。两者显式冲突时安装器在 Preview 阶段失败且不写文件。

### 已知拒绝条件

`--connect` 会在以下情况拒绝执行：

- `config get` 返回 `__OPENCLAW_REDACTED__`（无法安全整组回写）
- 主配置含 `$include`（可能修改未纳入事务快照的文件）

### 版本要求

OpenClaw CLI 要求 Node.js `>=22.22.3 <23`、`>=24.15.0 <25` 或 `>=25.9.0`。AGI Super Team 自身仍支持 Node 18+，该约束仅在调用 OpenClaw CLI 时适用。

本机实测版本：OpenClaw 2026.6.8。

## 未做的事

本仓库**未**把 AGI Super Team 封装为 OpenClaw 插件（无 `openclaw.plugin.json`）。当前只走安装器的文件落盘 + 配置合并路径。

## 相关文档

- [装配机制总览](./README.md)
- [harness-adapters.md](../guides/harness-adapters.md) — 版本化路径依据
- [OpenClaw — Plugins](https://docs.openclaw.ai/tools/plugin)
