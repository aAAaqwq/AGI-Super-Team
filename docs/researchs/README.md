# 调研记录

本目录存放**调研文档**：对某个问题做过系统调查后留下的结论、证据分级与待验证项。

与 [guides](../guides/) 的区别：guides 是面向使用者的稳定说明，调研记录**可能包含未验证项和更正记录**，会随新证据修订。

## 写作约定

- 每条结论标注证据等级：`[实测]` / `[官方]` / `[社区]` / `[未验证]`
- **未验证的内容必须显式标注**，不得作为实现依据
- 结论被推翻时保留**更正记录**，而不是静默改写

## 总览

- [**各 Coding Agent 的装配机制**](./coding-agent-assembly.md) — 六家框架的统一策略、跨工具标准与对比矩阵。**从这里开始。**

## 逐框架

| 框架 | 文档 | 状态 |
|---|---|---|
| Codex | [adapter-codex.md](./adapter-codex.md) | ✅ 端到端实测 |
| Claude Code | [adapter-claude-code.md](./adapter-claude-code.md) | ✅ marketplace 校验通过 |
| OpenClaw | [adapter-openclaw.md](./adapter-openclaw.md) | ✅ 安装器路径可用 |
| Hermes | [adapter-hermes.md](./adapter-hermes.md) | ✅ 安装器路径可用 |
| Gemini CLI | [adapter-gemini.md](./adapter-gemini.md) | ⚠️ **[官方] 机制成立，未实测** |
| Cursor | [adapter-cursor.md](./adapter-cursor.md) | ✅ 字段违规已修（`skillsDir`→`skills`）；客户端加载未证实 |
| Kimi | [adapter-kimi.md](./adapter-kimi.md) | ⚠️ **不自动生效（官方已证否）** |
| DeepSeek Harness | [adapter-dsh.md](./adapter-dsh.md) | ❌ **本仓库不支持** |

状态含义：

- ✅ 有实测证据
- ⚠️ 有官方文档依据但**未实测客户端行为**
- ❌ 已核实为**不可用或需修**（字段违规 / 机制不支持 / 本仓库未实现）

> **2026-09 复核**：Cursor / Gemini / Kimi 三家首次做了「位置 **与字段** 分开核实」。结论是三者性质各不相同——
> Gemini 位置与字段都对（唯一无字段错误），Cursor **字段曾写错**（`skillsDir` 应为 `skills`，官方 schema `additionalProperties: false` 使旧值在**校验口径**下不合规）**已修复**，
> Kimi 位置与字段都对但**官方明示客户端不自动读取仓库内 manifest**。详见各文档「结论先行」。

## 相关

- [DSH primary adapter 实施计划](../plans/dsh-primary-adapter.md) — 把 DSH 纳入支持的设计草案
- [Adapter 注册机制](../architecture/adapter-registration.md) — 代码层注册与校验
- [harness-adapters.md](../guides/harness-adapters.md) — 五个主力框架的落盘位置与接线
