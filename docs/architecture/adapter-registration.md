# Adapter 注册机制

这份文档记录 Adapter 在代码里**实际是如何注册和被校验的**，供维护者与准备接入新框架的人使用。

安装产物的落盘位置、接线行为与凭据要求见 [四个主力框架 Adapter 接入手册](../guides/harness-adapters.md)。本文只讲注册机制本身。

## 两个层级，不要混淆

仓库里有**两套**容易混淆的 Adapter 概念：

| 层级 | 载体 | 数量 | 作用 |
|---|---|---|---|
| **CLI 目标** | `config/cli-adapters.json` 的一个条目 | 19 个 | 声明一个框架的安装目标：路径、产物模式、支持状态 |
| **外置 Adapter 模块** | `config/harness-adapters/<id>.json` + `bin/adapters/<id>.mjs` | 5 个 | 只有主力框架才有，负责把 canonical Team 翻译成该框架原生格式 |

**只有 5 个主力框架**（Claude Code、Codex、OpenClaw、Hermes、DSH）拥有第二层。其余 14 个目标走安装器的通用渲染逻辑，不需要 `bin/adapters/*.mjs`。

判断一个框架属于哪一类，看它的条目有没有 `adapterModule` 字段。

## 第一层：CLI 目标注册

`config/cli-adapters.json` 是唯一的声明源，通过 `bin/installer/catalog.mjs` 的 `loadCatalog()` 加载并校验。

### 条目形态

```json
{
  "id": "claude-code",
  "label": "Claude Code",
  "scope": "global",
  "agentMode": "harness-adapter",
  "skillMode": "native",
  "agentPaths": [".claude/agents"],
  "skillPaths": [".claude/skills"],
  "support": "pending",
  "runtimeEvidence": "pending",
  "skillSource": "canonical-assigned",
  "adapterModule": "bin/adapters/claude-code.mjs",
  "connectionPath": ".claude/agi-super-team/connection.json"
}
```

没有外置 Adapter 的框架省掉 `adapterModule`、`connectionPath`，并使用更简单的 `agentMode`（如 `markdown`、`combined-rules`）：

```json
{
  "id": "qwen",
  "label": "Qwen Code",
  "scope": "global",
  "agentMode": "markdown",
  "skillMode": "native",
  "agentPaths": [".qwen/agents"],
  "skillPaths": [".qwen/skills"],
  "support": "adapter"
}
```

### 校验规则（`catalog.mjs`）

| 规则 | 位置 |
|---|---|
| `schemaVersion` 必须为 `1` | `catalog.mjs:33` |
| `tools` 必须恰好 **19** 个 | `catalog.mjs:33` |
| `id` 合法（`SAFE_ID`）、唯一 | `catalog.mjs:39` |
| `scope` 必须是 `global` 或 `project` | `catalog.mjs:39` |
| 必须声明 `agentPaths` 和 `skillPaths` 两个数组 | `catalog.mjs:42` |
| 主力框架（`priorityHarnesses`）必须额外声明完整契约 | `catalog.mjs:45-54` |

`priorityHarnesses` 硬编码为 `claude-code`、`codex`、`openclaw`、`hermes`、`dsh`。属于这一集合的目标必须满足：

```js
tool.agentMode === "harness-adapter"
&& tool.runtimeEvidence === "pending"
&& tool.skillSource === "canonical-assigned"
&& typeof tool.adapterModule === "string"
&& typeof tool.connectionPath === "string"
```

### 路径安全约束

主力框架的 `adapterModule` 会被**逐字比对**，且必须解析为受控目录下的真实文件：

```js
if (
  tool.adapterModule !== `bin/adapters/${tool.id}.mjs`
  || !isPhysicalStrictDescendant(adapterRoot, adapterPath)
) {
  throw new Error(`unsafe ${tool.id} Adapter module: ${tool.adapterModule}`);
}
```

也就是说，模块路径不能自定义、不能指向 `bin/adapters/` 之外、不能是符号链接。**`v1.5.0` 之前存在的安全修复**（拒绝符号链接目标）在这里同样生效。

### 三处 19 个的硬约束

新增或移除一个 CLI 目标，会**同时打破**三个独立的检查点：

| 检查点 | 内容 |
|---|---|
| `bin/installer/catalog.mjs:33` | 运行时抛错 `CLI adapter manifest must contain exactly 19 tools` |
| `tests/test_multi_cli_installer.py:113` | `test_adapter_manifest_has_exactly_nineteen_unique_tool_ids` |
| `tests/windows_cli_smoke.mjs:83` | 打包后 CLI 的 `--list-tools` 必须返回 19 个唯一 id |

**这意味着当前架构不支持增量式地"加一个框架"。** 接入新框架必须同步修改上述三处，并明确这是有意的契约变更，而不是绕过检查。

## 第二层：外置 Adapter 模块

### 模块注册表

`bin/adapters/index.mjs` 是静态注册表，**没有动态发现或插件机制**：

```js
const ADAPTERS = new Map(
  [claudeCode, codex, openclaw, hermes].map((adapter) => [
    adapter.ADAPTER_ID,
    adapter,
  ]),
);
```

模块被显式 `import` 后按 `ADAPTER_ID` 入 Map。`adapterFor(id)` 取不到时抛 `missing external Adapter module`。

### 导出的契约

每个模块必须导出：

| 导出 | 类型 | 用途 |
|---|---|---|
| `ADAPTER_ID` | `string` | 注册键，必须与目录名、清单 `id` 一致 |
| `renderAdapterArtifacts` | `function` | 生成该框架原生格式的 Agent/Skill 产物 |
| `buildConnectionSpec` | `function` | 生成 `connection.json` 接线凭据 |

`adapterFor()` 会校验后两个字段存在，否则抛 `invalid external Adapter module`。

### 声明式契约

`config/harness-adapters/<id>.json` 描述该框架的接线契约，由同名 `*.schema.json` 校验（另有共享的 `receipt.schema.json`）：

```json
{
  "$schema": "./claude-code.schema.json",
  "schemaVersion": 1,
  "harness": "claude-code",
  "connectionMode": "filesystem-discovery",
  "coordinator": "ast-ceo",
  "independentReviewer": "ast-governor",
  "requiredMaxDepth": 2,
  "maxConcurrentChildren": 2,
  "agentPath": ".claude/agents",
  "skillPath": ".claude/skills",
  "agentMap": { "ceo": "ast-ceo", "...": "..." },
  "delegation": { "...": "..." },
  "cleanClientReceipt": { "...": "..." }
}
```

层级与并发由契约固定：最大深度 2、每个 Manager 最多 2 个并发直属叶子。

## 接入一个新主力框架：需要动什么

以一个假想的框架 `foo` 为例，最小完整改动集：

1. `config/cli-adapters.json` —— 新增条目，且**三处 19 个的约束同步调整**。
2. `bin/adapters/foo.mjs` —— 实现 `ADAPTER_ID`、`renderAdapterArtifacts`、`buildConnectionSpec`。
3. `bin/adapters/index.mjs` —— `import` 并加入 `ADAPTERS` Map。
4. `config/harness-adapters/foo.json` + `foo.schema.json` —— 声明式接线契约。
5. 若该框架属于主力集合，`catalog.mjs` 的 `priorityHarnesses` 需要同步。

改动后必须通过：

```bash
npm test          # 含 19 个约束的契约测试
npm run validate:strict
```

## 已知缺口

- **没有运行时注册机制。** CLI 目标与 Adapter 模块都是编译期/静态注册，`--help` 中没有自定义 Adapter 注册标志。第三方框架无法在不改仓库的前提下接入。
- **19 个是硬编码常量**，不是可推导值。新增框架是一次契约变更，需要同时改代码与测试。
- **`priorityHarnesses` 是硬编码集合**，新增主力框架需要改 `catalog.mjs`。
