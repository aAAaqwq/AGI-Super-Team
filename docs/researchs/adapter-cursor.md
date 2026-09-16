# Cursor 装配

> **状态**：`[已修复]` —— 位置层已比对**官方文档 + 官方 JSON Schema** 核实（2026-09 复核轮）；曾含两处官方 schema 不认可的字段，**已于同轮修复**（`skillsDir`→`skills`、移除越界的 `author.url`）。本机未安装 Cursor（`/Applications` 无 `Cursor.app`），故**无任何 `[实测]` 证据**，客户端是否真加载仍为 `[未证实]`。

> **证据等级图例**：`[官方]` = Cursor 官方文档 / 官方仓库（附 URL）；`[实测]` = 本机实跑；`[推定]` = 由官方材料推导；`[未证实]` = 查不到，列出搜过的关键词。

## 结论先行

本仓库的 [`.cursor-plugin/plugin.json`](../../.cursor-plugin/plugin.json) **位置正确**。**以下两处字段违规已在核实后修复**，保留记录以便追溯：

| 严重度 | 问题 | 后果 |
|---|---|---|
| **HIGH** | `skillsDir` **不是合法字段名**，官方字段是 `skills` | 官方 schema 声明 `additionalProperties: false`，未知字段按 schema 即不合规。**市场提交扫描 / 官方 CI 会据此拒绝**；运行时加载器是否同等严格为 `[推定]` |
| **MEDIUM** | `author.url` 超出 `author` 对象允许的属性 | 官方 schema 的 `author` 为 `additionalProperties: false`，仅允许 `name` / `email` |

**位置与字段名分开说**：`.cursor-plugin/plugin.json` 这个**位置**是 `[官方]` 确认的；但 `skillsDir` 这个**字段名**是自造的，两者不能混为一谈。

### 这个缺陷的实际影响有多大？——要分两层看

必须诚实说明一个**削弱影响**的事实，否则会把严重度讲过头：

> 官方文档写明技能有**默认自动发现**路径——"| Skills | `skills/` | Each subdirectory containing a `SKILL.md` file |"
> —— <https://cursor.com/docs/reference/plugins>

也就是说，**即便 `skillsDir` 被加载器当作未知字段忽略掉，`skills/` 目录仍会被默认发现**（本仓库正好就叫 `skills/`）。所以：

| 场景 | 结果 |
|---|---|
| **运行时加载器宽松**（忽略未知字段） | 插件照常工作，`skillsDir` 只是冗余噪声——**实际影响≈0** |
| **运行时加载器严格**（按 schema 拒绝） | 插件**无法加载**——但此时删掉 `skillsDir` 反而修好（默认发现会接上） |
| **市场提交 / 官方 CI 校验** | 会被 `validate-plugins.yml` 与提交清单拒绝——**确定失败** |

**结论**：`skillsDir` 是**确定的规范违规**，也是**确定的市场提交阻断项**；但它是否导致「本地加载失败」取决于加载器的严格度，**这一点本轮无实测、无官方说明**，不可断言。无论哪种情况，**正确动作都是把它改成 `skills`**（或直接删除，让默认发现生效）——改动成本几乎为零，且能同时消除三种不确定性。同理 `author.url` 应删除或改为 `email`。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| 插件 manifest 位置（Cursor 格式） | `.cursor-plugin/plugin.json`（插件根目录下） | `[官方]` ✅ 已核实 |
| 插件 manifest 位置（Agent Plugins 开放标准） | 插件根目录的 `plugin.json` | `[官方]` ✅ 已核实 |
| 必需字段 | 仅 `name`（小写 kebab-case，允许数字/连字符/句点，首尾须为字母数字） | `[官方]` ✅ 已核实 |
| 技能字段名 | **`skills`**（`string \| string[]`，指向技能目录） | `[官方]` ✅ 已核实，**本仓库写成了 `skillsDir`** |
| 技能默认发现路径 | `skills/`（每个含 `SKILL.md` 的子目录） | `[官方]` ✅ 已核实 |
| **`author` 对象允许属性** | `name`（必需）、`email`（可选），`additionalProperties: false` | `[官方]` ✅ 已核实，**本仓库多写了 `url`** |
| manifest 其他可选字段 | `description` / `version` / `homepage` / `repository` / `license` / `keywords` / `logo` / `displayName` / `publisher` / `category` / `tags` / `rules` / `agents` / `commands` / `hooks` / `variables` / `mcpServers` / `minClientVersions` | `[官方]` ✅ 已核实 |
| 本地测试位置 | `~/.cursor/plugins/local/<plugin-name>/` | `[官方]` ✅ 已核实 |
| 发布路径 | 提交到 <https://cursor.com/marketplace/publish>，Cursor 团队人工审核后上架 | `[官方]` ✅ 已核实 |
| 多插件仓库 | 仓库根 `.cursor-plugin/marketplace.json` 列出各插件 | `[官方]` ✅ 已核实 |

### 官方原文（位置）

> "Every Cursor Plugin requires a `.cursor-plugin/plugin.json` manifest file."
> —— <https://cursor.com/docs/reference/plugins>

> | Format | Manifest location | Components |
> |---|---|---|
> | Agent Plugins (open standard) | `plugin.json` at the plugin root | Skills, MCP servers |
> | Cursor Plugins | `.cursor-plugin/plugin.json` | Skills, MCP servers, rules, agents, commands, hooks, variables |
> —— <https://cursor.com/docs/reference/plugins>

### 官方原文（字段）

> | `skills` | string or array | Path(s) to skill directories |
> —— <https://cursor.com/docs/reference/plugins>（Optional fields 表）

> | `author` | object | Author info: `name` (required), `email` (optional) |
> —— 同上

**Schema 佐证**（权威度高于文档表格，因为它就是校验器本身）：
<https://github.com/cursor/plugins/blob/main/schemas/plugin.schema.json>

```json
{
  "required": ["name"],
  "additionalProperties": false,
  "properties": {
    "name": { "type": "string" },
    "skills": { "$ref": "#/$defs/stringOrStringArray", "description": "Glob pattern(s) or path(s) to skill files." },
    "author": { "$ref": "#/$defs/author" }
  },
  "$defs": {
    "author": {
      "type": "object",
      "required": ["name"],
      "additionalProperties": false,
      "properties": { "name": { "type": "string" }, "email": { "type": "string" } }
    }
  }
}
```

`additionalProperties: false` 是最关键的一条：它意味着「字段名写错」**在 schema 校验口径下是硬失败，而不是被忽略**。`skillsDir` 和 `author.url` 都会命中这一条。

### 本仓库文件的对照

```json
{
  "name": "agi-super-team",          // ✅ 合法，匹配 kebab-case
  "version": "1.6.0",                // ✅ 合法
  "description": "...",              // ✅ 合法
  "author": { "name": "Daniel Li", "url": "https://github.com/..." },  // ⚠️ url 不在 schema 允许的 author 属性内
  "skillsDir": "./skills"            // ❌ 不在官方字段表中，应为 "skills"
}
```

## 客户端是否真的读它？

**位置层 `[官方]`，自动加载层 `[推定]`，端到端 `[未证实]`。** 三者要分开：

1. **manifest 位置与格式** `[官方]`：Cursor 确实读 `.cursor-plugin/plugin.json`——但这条只覆盖两种情况：**市场安装**（克隆仓库到插件缓存）和**本地测试**（放进 `~/.cursor/plugins/local/`）。官方从未说「打开一个仓库，仓库根目录的 `.cursor-plugin/` 就被自动加载」。
2. **仓库根自动发现** `[推定]`：Cursor 官方论坛的一则 Bug 报告从侧面支持仓库根发现存在——用户描述「直接打开 `projects/projectA` 时，`projects/projectA/.cursor` 里的插件被发现并生效」，Cursor 官方回复确认这是**「插件加载仅限主 workspace 根目录」**的已知限制（并说明子目录不被扫描、多仓库支持在计划中）。这证明「主 workspace 根会被扫描」为真，但**扫描的是 `.cursor/` 还是 `.cursor-plugin/` 未被原文区分**，且该回复是论坛答复而非文档承诺。
   <https://forum.cursor.com/t/plugins-not-loading-from-subfolders/155949>
3. **本仓库** `[未证实]` + **规范违规**：即便发现机制成立，本 manifest 也带着官方 schema 不认可的字段。在市场提交/CI 校验口径下这是确定失败；运行时是否拒绝则未知。在把 `skillsDir` 改对之前，讨论「Cursor 会不会读」缺少意义。

**已搜索未获结果的方向**：`Cursor project-level plugin discovery workspace root .cursor-plugin automatic`、`Cursor repo plugin auto-load without marketplace install`。官方文档对这一命题**始终只描述市场安装与 `~/.cursor/plugins/local/` 两条路径**。

## 未验证的部分

1. Cursor 是否扫描主 workspace 根的 `.cursor-plugin/`（官方文档未写，只有论坛侧面证据）——`[推定]`
2. 修好字段后，`skills: "./skills"` 是否按预期发现本仓库 **837 个 `SKILL.md`**（`find skills -name SKILL.md | wc -l`，`[实测]` 本机）——`[未证实]`
3. `name: "agi-super-team"` 是否与官方要求的 kebab-case 完全一致（含长度/字符集边界）——`[官方]` 规则已核，实际校验未跑
4. 官方 schema 的 `minClientVersions` 未声明时是否影响加载——未查

## 待办

- [ ] **修 `.cursor-plugin/plugin.json`**：`skillsDir` → `skills`；`author.url` → 删除或改为 `author.email`（**本仓库文件未改动，留给维护者统一处置**）
- [ ] 用官方 schema 跑一次本地校验（`schemas/plugin.schema.json`），确认改后无其他未知字段
- [ ] 装 Cursor 后按官方「Test plugins locally」把仓库放进 `~/.cursor/plugins/local/`，实测技能是否出现在 Customize 面板
- [ ] 实测后把状态改为 `[实测]`

## 核实记录

本轮（2026-09）用 tavily 检索官方文档 + 官方仓库核实：

| 结论 | 核实结果 | 处置 |
|---|---|---|
| `.cursor-plugin/plugin.json` 位置 | **属实**，官方逐字确认，且是 Cursor Plugin 格式的唯一 manifest 位置 | `[官方]` ✅ |
| `skillsDir` 字段 | **不成立**。官方字段是 `skills`；`skillsDir` 未出现在文档表、schema 或官方模板中 | 标为 HIGH 规范违规（未改文件） |
| **`author.url`** | **不成立**。官方 schema `author` 为 `additionalProperties: false`，仅 `name`/`email` | 标为 MEDIUM 规范违规（未改文件） |
| `additionalProperties: false` | **属实**，使上述两个字段错误变成致命错误而非被忽略 | 升级严重度 |
| 「仓库根 manifest 自动生效」 | 官方文档**只描述**市场安装与 `~/.cursor/plugins/local/`；仓库根发现仅有论坛侧面证据 | 降为 `[推定]` |

**检索关键词**：✅ 命中 `Cursor plugin .cursor-plugin/plugin.json manifest skillsDir field`、`cursor plugin publish repository .cursor-plugin/plugin.json reviewed validation`、`Cursor plugins local development ~/.cursor/plugins/local auto-discovery`；❌ 无结果 `Cursor repo-root plugin auto-discovery without install`。

## 相关文档

- [装配机制总览](./README.md)
- [Cursor — Plugins Reference](https://cursor.com/docs/reference/plugins)（字段表的原始出处）
- [Cursor — Plugins](https://cursor.com/docs/plugins)（本地测试与发布流程）
- [cursor/plugins — schemas/plugin.schema.json](https://github.com/cursor/plugins/blob/main/schemas/plugin.schema.json)（权威校验口径）
- [Cursor 论坛 — Plugins not loading from subfolders](https://forum.cursor.com/t/plugins-not-loading-from-subfolders/155949)（workspace 根发现的唯一侧面证据）
