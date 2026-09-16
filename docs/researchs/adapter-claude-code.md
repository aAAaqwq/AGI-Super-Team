# Claude Code 装配

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| marketplace 位置 | **必须**在仓库根 `.claude-plugin/marketplace.json` | `[官方]` |
| 校验 | `claude plugin validate <path>`（`--strict` 可把警告当错误） | `[实测]` |
| 插件本体位置 | 通过 `metadata.pluginRoot`（v2.1.239+）可收拢到 `plugins/` | `[官方]` |
| 技能根 | `~/.claude/skills/` | `[官方]` |
| Agent 格式 | Markdown + YAML frontmatter | `[官方]` |

### 目录名不可移动

Claude Code 的加载器**强制** marketplace 位于 `.claude-plugin/marketplace.json`，否则报错：

```
No manifest found in directory. Expected .claude-plugin/marketplace.json or .claude-plugin/plugin.json
```

这是客户端写死的发现约定，**改名即放弃 Claude Code 支持**。

### `source` 路径解析规则

- 相对 **marketplace 根**解析（即含 `.claude-plugin/` 的目录），不是相对 `.claude-plugin/` 本身
- **不允许 `../`** 引用 marketplace 根之外
- `metadata.pluginRoot`（v2.1.239+）允许用简写名，如 `"pluginRoot": "./plugins"` 让 `"formatter"` 解析到 `./plugins/formatter`

这是把插件本体收拢到 `plugins/` 的**官方途径**。

## 实测记录

```bash
claude plugin validate .
```

```
Validating marketplace manifest: .claude-plugin/marketplace.json
✔ Validation passed
```

补 `author` 字段前有 1 个警告：

```
⚠ Found 1 warning:
  ❯ plugins[0] plugin.json → author: No author information provided.
```

补齐 `author` 后**零警告通过**。

## Agent 装配

- Markdown 格式：`~/.claude/agents/ast-*.md`
- 由 Claude Adapter 生成，带 YAML frontmatter（`name` / `description` / `model` / `skills`）
- 可委派的角色不带 `disallowedTools: Agent`；叶子 Agent 与 Governor 带

## 本仓库的装配方式

安装器路径：`--tool claude-code --install --connect`，写 `~/.claude/agents/` 与 `~/.claude/skills/`。实测写入 170 个技能目录。

**未使用插件路径**：`plugins/` 下目前只有 Codex 形态的包。若要用 `pluginRoot` 收拢，需新增 Claude 形态的插件包。

## 相关文档

- [装配机制总览](./README.md)
- [Codex 装配](./adapter-codex.md)
- [Claude Code 插件市场官方文档](https://code.claude.com/docs/en/plugin-marketplaces)
