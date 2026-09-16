# Documentation index

Entry point for everything under `docs/`.

`docs/` is both the GitHub Pages artifact and an editorial navigation surface. It is **public navigation, not source authority** — see [repository architecture](./architecture/repository-architecture.md) for what that means.

## 目录结构

```text
docs/
├── README.md              本索引
├── architecture/          仓库架构与决策依据
├── guides/                安装、使用、兼容性说明（含已上线 HTML）
├── researchs/             调研记录（可能含未验证项）
├── plans/                 未实施的计划与提案
├── reference/             清单与目录索引
├── adr/                   已接受的架构决策（不可变）
├── evidence/              证据与技能治理
├── assets/ data/          站点资源与生成数据
└── *.html                 GitHub Pages 页面
```

## 架构

- [**Repository architecture map**](./architecture/repository-architecture.md) — 整仓库结构：五层、21 个权威源、顶层路径归属、接缝、变更对照、删除测试。派生自 [`config/repository-architecture.json`](../config/repository-architecture.json)。
- [Adapter 注册机制](./architecture/adapter-registration.md) — Adapter 在代码里如何注册与校验，含「恰好 18 个工具」三处硬约束。
- [Team / C-suite / Subagent / Skill 连接原理](./guides/team-agent-skill-architecture.md) — canonical 团队如何选型与路由。
- [路由分级与强制层](./guides/routing-and-enforcement.md) — L0–L3 路由与各 harness 的强制边界。
- [架构决策记录](./adr/) — 见其 [索引](./adr/README.md)。
- [Repository context](../CONTEXT.md) — 共享架构与产品语言。
- [Root architecture narrative](../ARCHITECTURE.md) — 权威长文版本。

## 调研

- [**各 Coding Agent 的装配机制**](./researchs/coding-agent-assembly.md) — Codex、Claude Code、OpenClaw、Hermes、Kimi、DSH 六家的插件机制、技能根与统一策略。含三处结论更正。
- [调研目录说明](./researchs/README.md)

## 安装与使用

- [主力框架接入手册](./guides/harness-adapters.md) — 四个主力框架的落盘位置与接线行为。
- [框架兼容性](./guides/harness-compatibility.html) — 各框架能强制什么、不能强制什么。
- [Claude Code 安装](./guides/claude-code-install.html) · [Codex 安装](./guides/codex-install.html)
- [选择团队形态](./guides/choose-ai-team.html) · 用例：[独立创始人](./guides/solo-founder.html) · [内容创作者](./guides/content-creator.html) · [量化研究](./guides/quant-research.html)

## 证据与发布

- [验证说明](./verification.html) — 结构检查与运行时凭据的区别。
- [npm 发布状态](./guides/npm-release-status.md) — npm/GitHub 发布漂移的诊断与结构性修复。
- [技能来源与评分](./skill-provenance-and-scoring.md) · [技能分类 Gold Set](./skill-taxonomy-gold-set.md)
- [数据目录](./data/) — 生成的统计与独立分类的验证凭据。

## 清单与参考

- [Docs 文件清单](./reference/docs-inventory.md)
- [100 个开发 Skill 待选清单](./reference/100-dev-skills-candidates.md)
- [Legacy Agent 矩阵](./skills-matrix.md)

## 站点

- [首页](./index.html) · [Guides 入口](./guides/index.html)
- [sitemap.xml](./sitemap.xml) · [404](./404.html)

---

Generated data must declare its builder and verification command in the [architecture registry](../config/repository-architecture.json). Return to the [repository README](../README.md).
