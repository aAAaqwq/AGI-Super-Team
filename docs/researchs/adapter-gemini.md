# Gemini CLI 装配

> **状态**：`[核实-机制成立]` —— 位置、字段名、机制**均比对官方文档原文核实通过**（2026-09 复核轮），是三个待核实入口中**唯一未发现字段错误**的一个。剩余的开放项是「安装后的扩展目录名是否与 `name` 一致」（`[推定]` 风险）与「`contextFileName` 指向文件的静默失败面」。本机未安装 Gemini CLI（`which gemini` 为空），故**无任何 `[实测]` 证据**。

> **证据等级图例**：`[官方]` = Gemini CLI 官方文档（附 URL）；`[实测]` = 本机实跑；`[推定]` = 由官方材料推导；`[未证实]` = 查不到，列出搜过的关键词。

## 结论先行

本仓库的 [`gemini-extension.json`](../../gemini-extension.json) **位置正确、字段名正确、机制成立**：

```json
{
  "name": "agi-super-team",              // ✅ 合法：纯 kebab-case（已用正则 [a-z0-9]+(-[a-z0-9]+)* 复核）
  "description": "...",                  // ✅ 合法
  "version": "1.0.0",                    // ✅ 合法（必填）
  "contextFileName": "CLAUDE.md"         // ✅ 字段名真实存在；值为任意文件名，合法
}
```

**与 Cursor 的对照**（本轮的判别力主要来自这个对照）：

| | Cursor | Gemini CLI |
|---|---|---|
| 位置有官方依据 | ✅ `.cursor-plugin/plugin.json` | ✅ 扩展根 `gemini-extension.json` |
| **字段名合法** | ❌ `skillsDir` 不存在（应为 `skills`） | ✅ **`contextFileName` 是真实字段名** |
| 值是否越界 | ❌ `author.url` 越界 | ✅ 无越界 |

Gemini 是三者中**唯一没有「字段名写错」问题**的入口。它剩下的都不是格式错误，而是**语义/运维层面的风险**（见下两节）。

## 机制

| 项目 | 值 | 证据 |
|---|---|---|
| manifest 位置 | 扩展目录**根**的 `gemini-extension.json`；发布时须在仓库/归档的**绝对根** | `[官方]` ✅ 已核实 |
| 安装方式 | `gemini extensions install <GitHub URL \| 本地路径>`，CLI **克隆一份到** `~/.gemini/extensions/<name>/` | `[官方]` ✅ 已核实 |
| `name` | **必填**，唯一标识 + 命令命名空间；小写、数字、连字符；须与扩展目录名一致 | `[官方]` ✅ 已核实 |
| `version` | **必填** | `[官方]` ✅ 已核实 |
| `description` | 可选，展示在 geminicli.com/extensions | `[官方]` ✅ 已核实 |
| `contextFileName` | **真实字段名**；`string \| string[]`；文件位于**扩展目录内**；默认 `GEMINI.md` | `[官方]` ✅ 已核实 |
| 其他可选字段 | `mcpServers` / `excludeTools` / `themes` / `settings` / `plan` / `migratedTo` / `hooks` | `[官方]` ✅ 已核实 |
| 变量 | `${extensionPath}` / `${workspacePath}` / `${/}` | `[官方]` ✅ 已核实 |
| 更新 | `gemini extensions update`（GitHub 源查 release tag / `git ls-remote`；本地源比 `version`） | `[官方]` ✅ 已核实 |
| 发布到官方画廊 | 仓库 public + 打 `gemini-cli-extension` topic + manifest 在绝对根；爬虫每日扫描 | `[官方]` ✅ 已核实 |

### 官方原文

> "Gemini CLI loads extensions from `/.gemini/extensions`. Each extension must have a `gemini-extension.json` file in its root directory."
> —— <https://geminicli.com/docs/extensions/reference>

> "`contextFileName`: The name of the file that contains the context for the extension. This will be used to load the context from the extension directory. If this property is not used but a `GEMINI.md` file is present in your extension directory, then that file will be loaded."
> —— <https://geminicli.com/docs/extensions/reference>

> "`name`: The unique identifier for the extension. Must be lowercase, use dashes instead of underscores or spaces, and match the extension directory name."
> —— <https://www.mintlify.com/google-gemini/gemini-cli/reference/extensions-api>

> "**Place the manifest at the root**: Ensure your `gemini-extension.json` file is in the absolute root of the repository or the release archive."
> —— <https://geminicli.com/docs/extensions/releasing>

**类型补充**（官方 API reference）：`contextFileName` 类型为 `string | string[]`，可加载多个上下文文件：

```json
"contextFileName": ["CONTEXT.md", "EXAMPLES.md"]
```

**本地/远端路径**：`gemini extensions install <source>` 支持 GitHub URL 或本地路径，另有 `--ref` / `--auto-update` / `--pre-release` / `--consent` / `--skip-settings`。

## 字段合法吗？

| 本仓库字段 | 判定 | 依据 |
|---|---|---|
| `name: "agi-super-team"` | ✅ **值合法** | 已用正则 `[a-z0-9]+(-[a-z0-9]+)*` 复核，纯 kebab-case；官方要求的字符集与「不要用下划线/空格」均满足 |
| `version: "1.0.0"` | ✅ | 必填字段，SEMVER 形态 |
| `description` | ✅ | 官方列为可选展示字段 |
| `contextFileName: "CLAUDE.md"` | ✅ **字段名与值均合法** | 字段名真实存在；值为任意文件名，官方示例含 `AWS_CONTEXT.md` / `CONTEXT.md` / `EXAMPLES.md`，**无任何规则要求必须叫 `GEMINI.md`** |

**本轮核实未发现 Gemini 入口的字段错误。** 与 Cursor 的 `skillsDir` 不同，`contextFileName` 拼写与语义都对得上官方文档。

## `contextFileName: "CLAUDE.md"` 到底怎么解析？

三个子问题分开答：

1. **是相对路径吗？** —— **是，且相对于扩展目录**。官方原文是 "load the context **from the extension directory**"。官方示例 `"contextFileName": "gemini-extension/GEMINI.md"` 带子路径，说明按扩展目录内的相对路径解析。`${extensionPath}` / `${workspacePath}` 这类变量用于 `mcpServers`，**不用于** `contextFileName`。

2. **能指向 `CLAUDE.md` 而不是 `GEMINI.md` 吗？** —— **能**。该字段的值是任意文件名（见上表）。**这一条彻底否定了「必须叫 GEMINI.md」的猜测**。

3. **在本仓库成立吗？** —— **成立，且比 Cursor 更干净**。`gemini extensions install <仓库 URL>` 会把**整个仓库**克隆到 `~/.gemini/extensions/<name>/`，仓库根的 `CLAUDE.md`（本仓库确有该文件）随克隆落地，`contextFileName: "CLAUDE.md"` 因而能解析到它。**成功的关键前提是 manifest 位于仓库绝对根——本仓库正是如此**，不像 Cursor 那样藏在 `.cursor-plugin/` 子目录里。

   ⚠️ **静默失败面（LOW）**：官方只在**未设置** `contextFileName` 时才回退到 `GEMINI.md`。**设置了但文件缺失 = 静默空上下文，不报错**。「`CLAUDE.md` 是本仓库为 *Claude Code* 维护的文件」这一点意味着：改它的人不会意识到它同时是 Gemini 扩展的上下文源，一旦改名/删除，Gemini 侧无声退化。

   > **建议（未改文件）**：① 增加根级 `GEMINI.md` 并显式写 `"contextFileName": ["GEMINI.md", "CLAUDE.md"]`（官方支持数组，双保险）；或 ② 维持现状，但在 `CLAUDE.md` 顶部标注「本文件同时是 Gemini 扩展的上下文源，勿改名」。

## 客户端是否真的读它？

**位置与机制 `[官方]`，端到端 `[未证实]`。**

- 「manifest 位于仓库根 → 被消费」这条链路**在本项目不需要额外假设**：官方机制就是「`gemini extensions install` 装一次、克隆一份、从克隆里读 manifest」，不存在 Cursor 那种「放仓库里会不会自动生效」的不确定性。这是 Gemini 入口**结构性优于 Cursor 的地方**。
- `gemini extensions list` 会回显解析到的上下文文件（第三方教程展示了 `Context files: /path/to/GEMINI.md` 的输出），可作为验收信号。
- **开放项 `[推定]`**：官方要求 `name` **与扩展目录名一致**，且 best-practices 把「name 匹配目录名」列为 `/extensions list` 不出现时的首要检查项。本仓库 GitHub 仓库名是 `AGI-Super-Team`（含大写），安装时 CLI 如何派生克隆目录名（是否小写化、是否去掉 `-release-1.6.0` 之类的后缀）**官方文档未写明**。若派生结果 ≠ `agi-super-team`，扩展可能不列出。**这是目前 Gemini 侧最值得实测的一点。**
- `[未证实]`：本机无 `gemini` CLI，未跑过 `gemini extensions install` / `list`。

**已搜索未获结果的方向**：`Gemini CLI repo-root manifest auto-load`（该命题在本项目**不适用**——官方只有 install 一条路，没有「放仓库即生效」的机制）。

## 未验证的部分

1. `gemini extensions install <本仓库 URL>` 后，克隆目录名是否等于 `agi-super-team`——`[推定]` 风险，见上
2. `/extensions list` 是否干净列出本扩展——`[未证实]`
3. `CLAUDE.md` 被当作 Gemini 上下文加载后，其内容（含 Claude Code 专属指令）是否对 Gemini 造成误导——**内容层风险，本轮未评估**

## 待办

- [ ] 装 Gemini CLI 后跑 `gemini extensions install <repo>` + `gemini extensions list`，**重点看目录名与 `name` 是否一致**
- [ ] 决定是否补根级 `GEMINI.md` 或改用数组 `contextFileName` 消除静默失败面
- [ ] 评估 `CLAUDE.md` 作为 Gemini 上下文的实际效果（是否需裁剪 Claude Code 专属段落）

## 核实记录

本轮（2026-09）用 tavily 检索官方文档核实：

| 结论 | 核实结果 | 处置 |
|---|---|---|
| manifest 位置 | **完全属实**，且官方额外强调「必须在**绝对根**」（本仓库满足） | `[官方]` ✅ |
| `contextFileName` 字段名 | **属实且拼写正确**——三个待核实入口中**唯一无字段错误的** | `[官方]` ✅ |
| `contextFileName` 的值可为任意文件名 | **属实**，官方示例含 `AWS_CONTEXT.md`/`CONTEXT.md`/`EXAMPLES.md` | `[官方]` ✅ |
| `contextFileName` 解析基准 | **扩展目录**（原文 "from the extension directory"），支持相对子路径 | `[官方]` ✅ 纠正了「可能相对 workspace」的猜测 |
| `contextFileName` 类型 | `string \| string[]`，可多文件 | `[官方]` ✅ |
| `name: "agi-super-team"` | **合法**（纯 kebab-case，本机正则复核 `_` 不存在） | `[官方]` ✅ **保留**；曾误记为含下划线，已自我更正 |
| `GEMINI.md` 兜底 | 只在**未设置** `contextFileName` 时生效；设了但文件缺失 = 静默空上下文 | 标为 LOW 风险 |
| `name` 须匹配安装目录名 | 官方明确要求；派生规则未写明 | 标为 `[推定]` 开放项 |

**检索关键词**：✅ 命中 `gemini-extension.json manifest fields contextFileName Gemini CLI extensions official documentation`、`Gemini CLI gemini extensions install github repository root`、`Gemini CLI extension manifest name must match extension directory name validation error`；❌ 无结果 `Gemini CLI repo-root manifest auto-load`（该机制不存在，官方只有 install 一条路）。

## 相关文档

- [装配机制总览](./README.md)
- [Gemini CLI — Extension reference](https://geminicli.com/docs/extensions/reference)（字段与 `contextFileName` 原文）
- [Gemini CLI — Build extensions](https://geminicli.com/docs/extensions/writing-extensions)
- [Gemini CLI — Release extensions](https://geminicli.com/docs/extensions/releasing)（绝对根要求）
- [Gemini CLI — Best practices](https://geminicli.com/docs/extensions/best-practices)（name/目录名排障）
- [Gemini CLI — Extensions API Reference](https://www.mintlify.com/google-gemini/gemini-cli/reference/extensions-api)（类型签名 `string | string[]`）
