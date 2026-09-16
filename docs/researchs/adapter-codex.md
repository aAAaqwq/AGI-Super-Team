# Codex 装配

Codex 的接入已有**端到端实测**，是本仓库当前验证最充分的路径。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| 插件市场 | `codex plugin marketplace add owner/repo` | `[官方]` |
| 仓库级 marketplace | `$REPO_ROOT/.agents/plugins/marketplace.json` | `[官方]` |
| 列插件 | `codex plugin list` | `[官方]` |
| 装插件 | `codex plugin add <name>@<marketplace>` | `[官方]` |
| 插件缓存 | `~/.codex/plugins/cache/$MARKETPLACE/$PLUGIN/$VERSION/` | `[实测]` |
| 技能根 | `~/.agents/skills/` | `[官方]` |

### 关于 `.codex-plugin/plugin.json`

它是**兼容回退**，不是必需。Codex 官方文档称 `.agents/plugins/marketplace.json` 为「repo marketplace」，`.claude-plugin/marketplace.json` 为「legacy-compatible marketplace」，而既有 `.codex-plugin/plugin.json`「remain supported as a compatibility fallback」。`[官方]`

本仓库**已删除**根级 `.codex-plugin/`（它是 `plugins/agi-super-team-codex/` 的重复副本），删除前经实测确认对插件发现无影响。

## 实测记录

codex-cli 0.153.4：

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

PLUGIN                               STATUS         SOURCE
agi-super-team-codex@agi-super-team  not installed  /tmp/probe/plugins/agi-super-team-codex
```

```bash
CODEX_HOME=/tmp/probe-home codex plugin add agi-super-team-codex@agi-super-team
```

```
Added plugin `agi-super-team-codex` from marketplace `agi-super-team`.
Installed plugin root: ~/.codex/plugins/cache/agi-super-team/agi-super-team-codex/1.6.0
```

### 删除根级 `.codex-plugin/` 的对照实验

同一组命令在**有**根级 `.codex-plugin/` 与**删除后**的两个副本上分别执行，`plugin list` 与 `plugin add` 输出**逐字相同**，插件均正常安装。

结论：该目录对 Codex 的插件发现无作用。

## Agent 装配

- Codex 使用 **TOML** 格式的 agent 文件：`~/.codex/agents/ast-*.toml`
- 主会话本身承担 CEO，**不生成第二个 CEO Agent**
- 当前主会话是 CEO，其余角色以 TOML 呈现

## 本仓库的装配方式

两种并存：

1. **安装器路径** —— `--tool codex --install`，写 `~/.agents/skills/` 与 `~/.codex/agents/*.toml`
2. **插件路径** —— 通过 `.agents/plugins/marketplace.json` 走 Codex 原生插件安装

### 附带收益

Codex 安装器的技能落盘位置是 `~/.agents/skills/`，这**同时被 DSH 和 Kimi 读取**。实测：`--tool codex --install` 写入 170 个技能目录。

## 相关文档

- [装配机制总览](./README.md)
- [Claude Code 装配](./adapter-claude-code.md)
- [Adapter 注册机制](../architecture/adapter-registration.md)
