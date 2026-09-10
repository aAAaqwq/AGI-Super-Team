# 5minbtc 版本归档

> **原则：旧版本引擎源码不留在本地**（不建 `archive/engines/`），只保留这份归档说明 + git 历史。
> 需要旧代码时从 git 取，不要在本目录堆积废弃 `.py`。

## 版本沿革

| 版本 | 日期 | 核心变化 | 源码能否取回 |
|------|------|---------|------------|
| v5.0 | ~2026-05 | 基础版（R14 审查 14 项修复） | ❌ 已不可考 |
| v5.1 | ~2026-05 | 动量窗口 30→15 防饱和；tanh 软饱和替代硬截断 | ❌ 已不可考 |
| v5.5 | 2026-05-26 | 116 轮 v5.4 复盘：Platt 置信度校准、中性区收缩、bull×0.92 惩罚 | ❌ 已不可考 |
| v5.6 | 2026-05-27 | R1–R4：趋势衰竭检测、volume 因子修复、V 型反转、Chainlink 对齐 | ❌ 已不可考 |
| v5.7 | 2026-05-28 | **半 K 线预测策略**（ATR×0.55，只预测剩余 ~55% 时间） | ❌ 已不可考 |
| v5.7.1 | 2026-06 | 黑天鹅防护（ATR spike + FNG<25 + news） | ❌ 已不可考 |
| v5.7.2 | 2026-06-17 | half_body vs imbalance 冲突裁决 | ❌ 已不可考 |
| v5.7.3 | 2026-06-17 | 引擎 HTTP 并行化（9 路） | ❌ 已不可考 |
| v5.7.4 | 2026-06-18 | TREND 强趋势 decel 极值约束 | ❌ 已不可考 |
| v5.8.0 | 2026-08-11 | `taker_buy` 因子 + 订单簿多时刻采样去噪 | ⚠️ 见下方说明 |
| v5.9.0 | 2026-08-13 | **对抗式审查重构**：13 因子收敛到 3 信号 + 三层过滤 + 多周期/跨资产/OFI | ✅ `50a4815` 前后 |
| v5.10.0 | 2026-08-17 | **概率套利**：去中性二选一 + `probability` 字段 + EV 下单 + 时段过滤 | ✅ `50a4815` |
| v6.0.0 | 2026-08-18 | **真 OFI 驱动**：方向一票交给订单流 + `P(close>open\|ofi)` + 错价 EV | ✅ `e893d31` |
| v6.0.0 (改名) | 2026-09-10 | 文件改名 `-v5.7.py` → `-v6.0.py`，版本标签对齐 | ✅ `dfa3047` |

各版本的详细变更见 [changelog.md](changelog.md)。

## ⚠️ v5.8 以前的源码已无法取回

两个原因叠加：

1. **本地不留旧版**（本文件开头的原则），只在改版时覆盖同名文件。
2. **仓库 git 历史被截断** —— `~/AGI-Super-Team` 是从 GitHub 重新 clone 的（旧的 `/tmp/AGI-Super-Team` 曾被系统清理损坏）。`skills/5minbtc/` 在仓库里**只有 7 个提交**，最早是 `d149f56`（2026-08-17）。

所以 git 里能查到的最早引擎快照 ≈ **v5.8 时期**，v5.0–v5.7 的代码**既不在本地也不在 git**，只在
[changelog.md](changelog.md) 的文字记录里留有行为描述。

> 原先还有一份 `performance-history.md` 记录 v4.x→v5.7.1 的逐日战绩，因其 83.0% 等数字已被
> [对抗式审查报告](strategy-adversarial-review.md) 证伪（真实 non-neutral 57.7% / bear 50.0%），
> 已于 2026-09-10 按最小无用原则删除；需要时从 git 历史取回。

## 取回历史版本

```bash
cd ~/AGI-Super-Team

# 列出引擎文件的所有历史提交
git log --oneline --all -- skills/5minbtc/5minbtc-engine-v5.7.py

# 取某个版本的引擎内容 (注意旧文件名)
git show 50a4815:skills/5minbtc/5minbtc-engine-v5.7.py > /tmp/engine-v5.10.py

# 对比两版差异
git diff e893d31 50a4815 -- skills/5minbtc/5minbtc-engine-v5.7.py
```

## 日志归档

`logs/` 采用「**当月 live + 历史按月压缩**」：

```
logs/
├── 5minbtc-log.jsonl                    # live，只含当月（不入库）
└── archive/
    └── 5minbtc-log.YYYY-MM.jsonl.gz     # 按月切分，写后不变（入库）
```

- 压缩归档**会同步进仓库**（`.gitignore` 里对 `logs/archive/*.gz` 做了逐级反忽略）。
- live 的 `*.jsonl` **不入库**（每 5 分钟追加，进 git 会产生巨大且无意义的 diff）。
- 轮转方法见 [setup-from-scratch.md](setup-from-scratch.md#日志轮转)。

## 2026-09-10 文档清理记录

按「最小无用原则」删除 11 份文档（references/ 由 34 份 → 23 份）。全部可从 git 历史取回：
`git show <sha>:skills/5minbtc/references/<文件名>`（删除前的提交见该文件的 git log）。

| 删除的文件 | 理由 |
|-----------|------|
| `performance-history.md` | 声称 v5.7.1 达 83.0%，已被[对抗审查](strategy-adversarial-review.md)证伪（真实 57.7% / bear 50.0%）；且引用 9 个不存在的 `review-*.md` |
| `architecture.md` | 仍把「13 正交因子」当方向模型（v5.9 已清零）、把 OFI 列为未来路线图（v6.0 已实现）；且代码围栏未闭合导致整篇被当代码渲染 |
| `decel-collapse-pattern.md` | 主张「LLM 应覆盖引擎方向」，与 v6.0「OFI 一票决定」+ 铁律 #4 直接冲突；decel 因子已清零 |
| `black-swan-defense-v571.md` | 补丁对象 `v_reversal`/`decel` 已清零；幸存内容（ATR spike + FNG<25）已在 SKILL.md 架构行 |
| `engine-parallelization-v573.md` | 描述「4 路并行」，现为 9 路；唯一有效的 pitfall 已存于 [pitfalls.md](pitfalls.md) #5 |
| `cron-setup.md` | 薄壳：版本同步规则与 pitfalls #7 重复，job 表已在 [cron-llm-provider-failure.md](cron-llm-provider-failure.md) §8（本次补入了原始 cron 表达式） |
| `polymarket-data-source.md` | 交易场所已换成币安 Web3 预测市场，Polymarket 盘口框架过时；Chainlink 价差风险仍在 pitfalls 的 `chainlink_offset` 条目 |
| `dreaming-cron-recovery.md` | 2026-06 单次事故记录，其数据源 fallback 建议从未落地；job 仍在，说明见 cron-llm-provider-failure.md §8 |
| `session-2026-06-17.md`、`session-2026-06-18.md` | 结论已 100% 蒸馏进 `lessons.md` #12/#14/#18 与 `changelog.md` v5.7.4 |
| `daily-stock-analysis-data-sources.md` | 无关内容：A 股/港股/美股股票项目的 fetcher 评估 |

同时删除 **6 个死函数**（详见 [output-template.md](output-template.md#13-已删除--仍残留的死代码)）：
引擎的 `calibrate_confidence`（v5.5 Platt 残骸）、realtime 的 `record_limit` / `fmt_limit` / `fmt_skip_knife`（已废弃的「甜区限价挂单」）与 `fmt_no_edge` / `fmt_signal`。

**保留判断**（看似重复但经复核不删）：Binance 三份网络文档是**三种不同故障模式**；
`reports/` R01–R14 被 [quant-knowledge-index.md](quant-knowledge-index.md) 索引；
`lessons.md` / `pitfalls.md` / `strategy-adversarial-review.md` 是「历史叙事 / 行动索引 / 权威结论」三种角色，互补而非重复。

## 归档 SOP（每次引擎升版时做）

1. 改版本号：引擎 docstring、`SKILL.md` frontmatter 的 `version:`、`README.md` badge。
2. **文件改名跟随版本**（如 `-v6.1.py`），避免再次出现「文件名 / 文档 / 代码」三个版本号打架。
3. 更新全量引用：`grep -rn "5minbtc-engine-v" --include='*.py' --include='*.md' .`
4. 在 [changelog.md](changelog.md) 顶部**新增**一节（不要改历史节）。
5. 在本文件的「版本沿革」表补一行，填上 commit hash。
6. 重启守护进程（`ENGINE` 是模块级常量，进程不会自动感知改名）：
   ```bash
   launchctl kickstart -k gui/$(id -u)/com.daniel.5minbtc-realtime
   launchctl kickstart -k gui/$(id -u)/com.daniel.5minbtc-watch
   launchctl kickstart -k gui/$(id -u)/com.daniel.5minbtc-paper
   ```
7. 同步仓库，见 [sync-procedure.md](sync-procedure.md)。
