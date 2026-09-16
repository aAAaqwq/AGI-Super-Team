# Docs directory inventory

`docs/` 下每个文件的清单。仓库整体结构见 [架构地图](../architecture/repository-architecture.md)，顶层索引见 [docs 索引](../README.md)。

## 目录布局

```text
docs/
├── README.md                        索引
├── architecture/                    架构与决策依据
├── guides/                          安装、使用、兼容性（含已上线 HTML）
├── researchs/                       调研记录
├── plans/                           未实施的计划
├── reference/                       清单与目录索引
├── adr/                             已接受的架构决策
├── assets/  data/                   站点资源、生成数据
├── index.html  verification.html    站点页面
├── sitemap.xml  404.html            搜索与失败路由
├── skill-provenance-and-scoring.md  技能来源评分
├── skill-taxonomy-gold-set.md       技能分类 Gold Set
└── skills-matrix.md                 Legacy Agent 矩阵
```

## architecture/

- [`repository-architecture.md`](../architecture/repository-architecture.md) — 整仓库架构地图，派生自 `config/repository-architecture.json`。
- [`adapter-registration.md`](../architecture/adapter-registration.md) — Adapter 的代码层注册与校验机制。
- [`repository-entrypoints.md`](../architecture/repository-entrypoints.md) — 六个 harness 入口对照与 canonical→分发→文档三层结构。

## guides/

- [`harness-adapters.md`](../guides/harness-adapters.md) — 四个主力框架的落盘位置与接线行为。
- [`team-agent-skill-architecture.md`](../guides/team-agent-skill-architecture.md) — Team / C-suite / Subagent / Skill 的连接原理。
- [`routing-and-enforcement.md`](../guides/routing-and-enforcement.md) — 路由分级与强制层。
- [`npm-release-status.md`](../guides/npm-release-status.md) — npm 发布漂移诊断与修复。
- [`claude-code-install.html`](../guides/claude-code-install.html) · [`codex-install.html`](../guides/codex-install.html) · [`openclaw-install.html`](../guides/openclaw-install.html) · [`hermes-install.html`](../guides/hermes-install.html) — 各框架安装指南。
- [`dsh-install.html`](../guides/dsh-install.html) — DeepSeek Harness 状态说明（尚未接入，含实测的手工接线方式）。
- [`harness-compatibility.html`](../guides/harness-compatibility.html) — 各框架能力边界。
- [`choose-ai-team.html`](../guides/choose-ai-team.html) — 团队选型。
- [`solo-founder.html`](../guides/solo-founder.html) · [`content-creator.html`](../guides/content-creator.html) · [`quant-research.html`](../guides/quant-research.html) — 用例。
- [`index.html`](../guides/index.html) — HTML 指南入口。

## researchs/

- [`coding-agent-assembly.md`](../researchs/coding-agent-assembly.md) — 六家 coding agent 的装配机制调研。

## plans/

- [`README.md`](../plans/README.md) — 计划目录约定（暂无计划）。

## reference/

- [`100-dev-skills-candidates.md`](../reference/100-dev-skills-candidates.md) — 待评审的开发 Skill 候选清单。

## 其他

- [`adr/`](../adr/) — 架构决策记录，见其 [索引](../adr/README.md)。
- [`data/`](../data/) — 生成的同源统计与独立分类的验证凭据；**不是权威来源**。
- [`assets/`](../assets/) — 站点图片与图标。
- [`index.html`](../index.html) · [`verification.html`](../verification.html) — 站点页面。
- [`skill-provenance-and-scoring.md`](../skill-provenance-and-scoring.md) · [`skill-taxonomy-gold-set.md`](../skill-taxonomy-gold-set.md) · [`skills-matrix.md`](../skills-matrix.md) — 技能治理与清单（因被生成产物引用而保留在顶层）。

---

生成数据必须在[架构注册表](../../config/repository-architecture.json)中声明其构建器与校验命令。返回[仓库 README](../../README.md)。
