# 原创 Skills 候选审计

审计日期：2026-08-02

本审计用于解释首批原创分类的收录边界。它不替代 `config/skill-provenance.json`；机器索引仍只接受 `project-original + reviewed`。

## 已使用的证据

- 当前正式 provenance 合同中的已审查第一方条目。
- 创建提交 `cecc3e42…` 中明确标记为 self-built 的内容工具与三条自媒体日更链路。
- 创建提交 `02262c4e…` 中的即梦、视频合并和视频号发布链路。
- 历史保守原创清单 `50253254…:skills/docs/original-skills.md`。
- `5minbtc` 的首个创建提交 `aae3f692…` 及后续仓库内迭代历史。
- Binance Square v4 的实现、优化提交和独立验证记录。
- `daniel-x-writer` 的完整个人 Skill 目录、风格样例、长度检查器及本次规范化同步提交。

## 首批结果

- 收录 32 个强证据原创 Skills。
- 明确包含 `binance-square`、`5minbtc`、`daniel-x-writer`、`daily-gzh-content`、`daily-xhs-content`、`daily-douyin-content`。
- 原创目录是索引视图，不复制第二份 Skill 内容；规范源仍为 `skills/<skill-id>/`。

## 暂不晋级的相邻候选

| 候选 | 当前处理 | 原因 |
|---|---|---|
| `btc-5min-scalper` | 已晋级（2026-11-03） | Daniel Li 确认为原创；创建提交、MIT 许可证与树摘要已补齐。 |
| `xhs-content-creator` | 排除 | 目录带外部 registry 来源记录，不能仅凭本地出现或作者提示改写为原创。 |
| `wechat-ai-radar` | 已晋级（2026-11-03） | Daniel Li 确认为原创；创建提交、MIT 许可证与树摘要已补齐。 |
| `wechat-article-writer` | 已晋级（2026-11-03） | Daniel Li 确认为原创；创建提交、MIT 许可证与树摘要已补齐。 |
| `xhs-writing-coach`、`cross-platform-poster` | 已晋级（2026-11-03） | Daniel Li 确认为原创；ClawHub 安装记录仅说明分发来源。 |
| 旧 Platform / Agent Operations 批次 | 待审计 | 批量添加 `author` 字段不能证明没有上游来源，需逐项核验提交前内容和许可证。 |

新增候选必须先补齐作者、创建提交、许可证、当前树摘要和来源证据，然后由生成器自动进入原创分类。不得手改 `README.md` 或 `index.json` 绕过 provenance。

## 2026-11-03 第二批

Daniel Li 于 2026-11-03 确认以下 26 个 Skill 为其原创。已按当前 provenance 合同补齐作者、创建提交、MIT 许可证证据和当前树摘要；`skills/original/` 索引相应从 39 增至 65。

`a-fund-monitor`, `a-share-analysis`, `ai-trader-arena`, `btc-5min-scalper`,
`daniel-auto-publish`, `daniel-new-media-ops`, `daniel-self-media-top-mindset`,
`daniel-wechat-writing`, `daniel-writer`, `daniel-xhs-writing`, `douyin-creator`,
`douyin-publisher`, `douyin-video-analyst`, `wechat-ai-radar`,
`wechat-article-writer`, `wechat-channel`, `wechat-personal-message`,
`wechat-pipeline`, `wechat-toolkit`, `xhs-skill`, `xhs-smart-publisher`,
`daniel-content-writing-style`, `agent-team-orchestration`, `agent-qa`,
`cross-platform-poster`, `xhs-writing-coach`

特殊说明：

- `agent-qa`：Daniel Li 确认指令内容原创；PR #42 由 Pranshu Chittora 提交。外部 agent-qa 运行时为 FSL-1.1-ALv2 单独授权，未随仓库打包。
- `agent-team-orchestration`、`cross-platform-poster`、`xhs-writing-coach`：`.clawhub/origin.json` 安装记录仅说明分发来源，不改变原创声明。
- `daniel-content-writing-style`：内容来自 Daniel 个人 IP 工作区，经多 Agent 审阅后同步；已补创建提交、许可证和当前树摘要。

仍未晋级：

- `xhs-content-creator`：带外部 registry 来源记录，维持排除。
- 旧 Platform / Agent Operations 批次：仍需逐项核验。

2026-11-03 已复核并刷新 stale 原创：`5minbtc`、`bb-scalper`、`binance-square`。三者的当前树摘要已与复核后的版本对齐。
