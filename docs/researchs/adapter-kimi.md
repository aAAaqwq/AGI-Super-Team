# Kimi 装配

> **状态**：`[未验证]` —— 以下依据来自 Kimi 官方文档，但**未在本机实测客户端行为**（本机未安装 `kimi` CLI）。在实测确认前，不得声称 Kimi 已支持。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| manifest 位置 1 | `.kimi-plugin/plugin.json` | `[官方]` |
| manifest 位置 2 | `kimi.plugin.json`（**优先级更高**） | `[官方]` |
| 两者同时存在 | 以 `kimi.plugin.json` 为准 | `[官方]` |
| 插件管理 | `kimi plugin` 命令 | `[官方]` |
| 插件安装位置 | `~/.kimi/plugins/<plugin>/` | `[官方]` |
| 数据根 | `$KIMI_CODE_HOME`（默认 `~/.kimi-code`） | `[官方]` |

### 本仓库已有的 manifest

`.kimi-plugin/plugin.json` **正是 Kimi 的官方合法位置之一**，不是自造：

```json
{
  "name": "agi-super-team",
  "version": "1.6.0",
  "description": "...",
  "author": { "name": "Daniel Li", "url": "..." },
  "skills": "./skills"
}
```

## 技能

| 项目 | 值 | 证据 |
|---|---|---|
| 技能格式 | `SKILL.md`（与 Agent Skills 开放标准一致） | `[官方]` |
| 用户级技能 | `~/.agents/skills/`、`$KIMI_CODE_HOME/skills/` | `[官方]` |
| 项目级技能 | `.kimi-code/skills/`、`.agents/skills/` | `[社区]` |
| 优先级 | 项目 > 用户 > 额外 > 内置 | `[官方]` |

**关键点**：`~/.agents/skills/` **同时被 Codex、DSH、Kimi 读取**。因此一次 Codex 安装（实测写入 170 个技能）理论上即可让 Kimi 也识别这些技能。

Kimi 文档亦称该路径与 Claude Code 共享同一 skill 根。

### 路径不受 `KIMI_SHARE_DIR` 影响

Kimi 官方特别说明：`KIMI_SHARE_DIR` 定制的是配置、会话、日志等运行时数据的位置，**不影响 Skills 搜索路径**。技能是跨工具共享能力，与应用运行时数据是不同类型。自定义技能路径要用 `--skills-dir` 或 `extra_skill_dirs` 配置。

## Agent 机制

- 插件可携带 `agents/` 目录，或通过 manifest 的 `agents` 字段声明 `./` 路径 `[官方]`
- Agent 文件格式与 Kimi 的自定义 Agent 相同（**Markdown**，接近 Claude Code 形态） `[官方]`
- 插件 Agent 的优先级**低于**其他文件来源：同名时用户级、额外目录、项目级与 `--agent-file` 都会覆盖
- 覆盖内置 Agent 需在 frontmatter 显式写 `override: true`
- 安装/启用/禁用/移除插件后，Agent 列表在新会话或 `/reload` 时刷新
- 插件可声明 `mcpServers` 复用 MCP schema

## 未验证的部分

以下都需要**实际安装 Kimi CLI 后实测**才能确认：

1. Kimi 是否真的读取并加载 `.kimi-plugin/plugin.json`
2. `skills: "./skills"` 字段是否指向本仓库 800+ 技能的根目录并按预期发现
3. `~/.agents/skills/` 中的技能是否被 Kimi 的 Agent Skills 系统识别
4. Kimi 的 agent 加载是否与 Claude Code 的 Markdown 格式完全兼容

## 待办

- [ ] 安装 Kimi CLI，实测 `kimi plugin` 是否识别本仓库
- [ ] 实测后把本文档的 `[未验证]` 标记改为 `[实测]` 并记录输出

## 相关文档

- [装配机制总览](./README.md)
- [Kimi Code — Plugins](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html)
- [Kimi Code — Data locations](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/data-locations.html)
