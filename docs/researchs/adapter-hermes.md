# Hermes 装配

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| 插件安装 | `hermes plugins install owner/repo --no-enable` | `[官方]` |
| 列出 | `hermes plugins list` | `[官方]` |
| 启用 | `hermes plugins enable <plugin-name>` | `[官方]` |
| 技能根 | `~/.hermes/skills/` | `[官方]` |
| 插件目录 | `~/.hermes/plugins/` | `[官方]` |
| 技能安装 | `hermes skills install <id>` | `[官方]` |

### 安装后默认禁用

`hermes plugins install` 装完后插件**处于禁用状态**，必须显式 `hermes plugins enable` 才会生效。这是 Hermes 的设计，不是失败信号。

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

### 安全扫描

每次 `hermes plugins install` / `update` 都会对插件树跑**静态安全扫描**（凭据外泄、反弹 shell、破坏性命令、持久化机制、混淆执行、文档中的提示注入）。

三档判定，与 Cowork 的 pass/warn/fail 对应。插件读取自己声明的环境变量（`requires_env`）不会被误报。

### 环境变量

非空 `HERMES_HOME` 是最终安装根。未设置时 POSIX 默认 `~/.hermes`，Windows 默认 `%LOCALAPPDATA%\hermes`。

**与 `--home` 冲突时安装器直接报错**：

```
error: --home conflicts with HERMES_HOME: /path/to/home
```

实测遇到过。两者只能给一个。

## 本仓库的装配方式

安装器路径：

```bash
npx -y agi-super-team@latest --tool hermes --install
```

- Agent 产物：`$HERMES_HOME/skills/agi-super-team-agents/ast-*/SKILL.md` + Profile 蓝图
- 技能产物：`$HERMES_HOME/skills/agi-super-team/<skill>`
- **不自动创建** Profile、Cron 或 Gateway

实测：隔离 HOME 下安装成功，写入 `~/.hermes/skills`。

## 未做的事

本仓库**未**提供 Hermes 形态的插件包（包根 `plugin.json`）。当前只走安装器。

若要支持 `hermes plugins install aAAaqwq/AGI-Super-Team`，需新增 `plugins/agi-super-team-hermes/`，且 `plugin.json` 放在包根而非 `.codex-plugin/` 子目录。

## 相关文档

- [装配机制总览](./README.md)
- [harness-adapters.md](../guides/harness-adapters.md) — `get_hermes_home()` 等版本化依据
- [Hermes — Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/)
