---
name: 5minbtc
version: 6.0.0
description: "BTC 5分钟K线实时方向预测 + 币安预测市场错价套利(paper)。v6.0 真OFI驱动: 方向由当前K线原生 in-candle OFI 净流一票决定(ofi_n=2*(tb/v)-1, REST klines[9] 聚合, 零WS依赖; WS ofi.json 做新鲜度反转保护与交叉校准), 概率=P(close>open|ofi) 经验校准表+Bayesian shrink, edge=EV=p−ask 错价检测, 方向二选一无中性。13因子自v5.9起收敛到3个有证据信号且不再决定bias。黑天鹅防护: ATR spike+FNG<25。launchd 常驻 realtime/watch/trader。Binance端点双向故障切换。"
triggers:
  - 5minbtc
  - 5min btc
  - btc 5min
tools:
  - terminal
  - web
---

# 5minbtc — BTC 5分钟实时预测 v6.0.0

> BTC 单根 5min K线 方向 + 收盘价预测。引擎+LLM 混合架构。
> **SKILL.md 是索引, 详细内容见 `references/`。**
> **v5.9 认知转变**: 从"13因子预测器"→"3信号错价检测器" — 方向准确率不是 edge, `EV = p − P − 成本` 才是 (见 [对抗式审查报告](references/strategy-adversarial-review.md))
> **v6.0 执行转变**: 方向从"body 延续统计"改成**真 OFI 净流一票决定** — 赌的是"净流已发生、token 价还没定价"的 flow-gap

> ⚠️ **同名易混**: 本 skill 只做 BTC 单标的 5min 方向 + 预测市场 EV。要做全市场永续的量价突破扫描, 用 [`coin-vp-scanner`](../coin-vp-scanner/SKILL.md) — 两者区别见下方 [与 coin-vp-scanner 的分工](#与-coin-vp-scanner-的分工)。

## 触发
`5minbtc` / `5min btc` / `btc 5min` / `监控` (配合持续盯盘)

## 何时使用
| 场景 | 做法 |
|------|------|
| 当前 5min K线 方向+价位 | ✅ 标准流程, **方向=OFI 净流, edge=错价 EV** (v5.8 零前视回测 61.4% 是延续性不是 alpha, 见性能快照) |
| 会话内持续盯盘, 等明确信号 | ✅ 监控模式 (scripts/5minbtc-monitor.py + Monitor 工具) |
| 币安预测市场 Up/Down 5m 交易 | ✅ paper 模拟/实时监控 (见 [预测市场策略](references/prediction-market-strategy.md)) |
| "今晚 BTC 涨跌" (宽窗口) | ⚠️ 跑当前 K线 + 给方向倾向, 标注"超出引擎置信区间" |
| "下根 K线" / "1小时后" | 引导在该 K线 起始时间再触发 |

## 监控模式 (Claude Code)

> 详见 [monitoring-claude-code.md](references/monitoring-claude-code.md)

```bash
# 无限持续, 直到用户喊停 (会话内盯盘推荐)
Monitor(command: "python3 <SKILL>/scripts/5minbtc-monitor.py --max-runs 0", persistent: true)

# 默认 20 次采样 (约 40 分钟)
python3 <SKILL>/scripts/5minbtc-monitor.py

# 单次判断 (非持续)
python3 <SKILL>/scripts/5minbtc-monitor.py --dry-run
```

- **明确信号** = bias 非中性 + strength∈{medium,moderate,strong} + conf≥50 → 自动停
  (⚠️ 实测引擎 strength 输出 `medium`, 判定集合需同时含 `medium` 和 `moderate`)
- 每根 K 线第 2/3 分钟采样 (progress ~40-70%), 比 cron 第 4 分钟更早
- 事件流: `START` / `DIR-CHANGE` / `CLEAR-SIGNAL` / `ENGINE-ERR` / `MAX-RUNS`
- 停止: 用户说「停/结束」→ `TaskStop` 停 Monitor
- `CLEAR-SIGNAL` 后必须拉一次完整引擎快照二次确认
- 引擎验证: `python3 -m pytest scripts/test_engine_v58.py -v` (12 项)

## 快速开始

```bash
SKILL_DIR=/home/aa/.hermes/profiles/cqo/skills/5minbtc

# 1. 并行: 引擎 + 新闻 + settle (前一根)
python3 $SKILL_DIR/5minbtc-log.py settle-all 2>&1
python3 $SKILL_DIR/5minbtc-engine-v6.0.py 2>&1
python3 $SKILL_DIR/5minbtc-news.py 2>&1

# 2. 3 路 web_search (并行)
# "Bitcoin BTC breaking news price" / "crypto market macro stocks today" / "比特币 BTC 最新 晚间"

# 3. LLM 分析 → 输出 (见 output-template.md)
# 4. 写日志
python3 $SKILL_DIR/5minbtc-log.py log \
  "<candle.iso>" <pred_close> <pred_high> <pred_low> \
  <conf> <bias> <news_sent> <vol_pct>
```

## 架构 (1 行/组件)
- **引擎** `5minbtc-engine-v6.0.py` (v6.0, 输出 `"version": "6.0.0"`): **bias 由真 OFI 净流一票决定** (ofi_n>0→bull / <0→bear, **二选一无中性**; ofi_n 缺失/为0 用 body 符号兜底并标 `meta.body_fallback`。弱信号/流量不足只让概率趋近 0.5 → EV 过滤不下单, 不产生 neutral) + **概率 `P(close>open|ofi)`** 三层(经验校准表 Bayesian shrink + flow-gap + 最近60s流) + 三层独立过滤(多周期4h/1h/15m 结构 + 跨资产ETH/SOL 广度 + WS OFI 新鲜度反转保护) + 9路并行HTTP
  - 门限: `T_OFI_GATE=0.20` / `T_OFI_60=0.35` / WS 质量闸 `OFI_CR_MIN=0.80` / `OFI_BAYES_N=30`
  - **13 因子仍计算并输出**(JSON 契约保留), 但自 v6.0 起**不参与 bias 决策** — score 只用于 `strength` 标签与 LLM 参考
- **订单流** `scripts/ofi_feed.py`: trade+bookTicker 组合流 tick规则推断主动买卖, 写 `~/bb-auto/ofi.json`, 带 ts 保鲜(>30s 引擎降级为只信 REST 主源) (launchd: com.daniel.ofi-feed)
- **日志** `5minbtc-log.py`: jsonl 追加 + 增量 settle (写入 logs/)
- **新闻** `5minbtc-news.py`: CoinDesk RSS (唯一稳定源, ~14min 延迟)
- **常驻进程** (launchd): `5minbtc_realtime.py` (5s 刷新, 预测快照+EV下单) / `5minbtc_watch.py` / `5minbtc_trader.py --paper-monitor`
- **LLM**: 因子打分基准 + LLM 综合裁决 + 模板输出

## 铁律
1. 每次必须重新执行引擎脚本 — 不缓存
2. 每次必须重新搜索3组新闻
3. 先 settle 上一根, 再 log 新预测
4. LLM 可微调引擎的 `pred_close`/range, 但必须说明理由
   ⚠️ **bias 不要轻易覆盖** (v6.0): 方向是 OFI 一票决定的, LLM 用因子/新闻翻方向 = 退回被证伪的路径。
   仅在 `meta.body_fallback=True` 或 OFI 数据缺失时才允许改 bias, 并显式写明原因。
5. 输出 15-25 行 (平衡深度和 Telegram 可读性)

## 关键裁决规则 (⚠️ 历史规则: v5.7.x 因子打分路径)

> **v6.0 起 bias 由真 OFI 一票决定, 下列规则不再决定方向。** 仅在两条兜底路径上仍有参考价值:
> ① `meta.body_fallback=True` (ofi_n 缺失/为0, 方向退回 body 符号) ② LLM 复核时解释 `meta` 冲突字段。
> 引擎的 `raw score` 仍输出, 但只影响 `strength` 标签, 不影响 bias。

- **half_body vs imbalance 冲突** (v5.7.2): |half_body|>0.25 + |imbalance|>0.5 + progress≥45% → 优先 half_body <sub>(注: 两者自 v5.9 起权重已清零)</sub>
- **TREND 强趋势 decel 约束** (v5.7.4): EMA delta>$100 时 |decel|>0.7 需 |half_body|>0.15 同向确认
- **fatigue≥0.8**: conf 上限 40, 反向 +10pp
- **chainlink_offset 矛盾**: bias=bull 但 pred_close<current → 以 current 为锚 ±ATR×0.3
- **极端进度 (>80%)**: pred_close 按剩余时间比例缩放
- **Body=0 持续模式**: pred_close → current ± ATR×0.2, conf 降至 35-42%

## 性能快照 (2026-09-10 更新)

> 数字口径以 [对抗式审查报告](references/strategy-adversarial-review.md) 为准 — 旧数字多数含前视偏差。

- **v5.7 回测 71.2% 含前视偏差**(文件里自己标注"已知"); 零前视 v5.8: 前2根1min=**61.4%**, 前4根=69.5%
- 但 61–70% 是"看着 K 线走完再确认"的延续性, **不是 alpha** — 做市商已把它定价进 token 价
- 去掉水分后的真实基准: non-neutral 方向 **57.7%** | bull **63.9%** (唯一显著) | **bear 50.0% = 纯硬币**
- paper 交易: 全样本 UP 成交 **44%** (+$0.24) | 甜区 UP ask 0.40–0.50 → **60%** (+$1.39) ← 唯一正 EV 区间
- **结论: edge 不在方向准不准, 在 `EV = p − P − 成本 > 0`。v6.0 的错价检测(flow-gap)就是直接做这件事。**
- 当前 LLM: `zai/glm-5.2` (8-15s/次) | opencaio 实测 MiniMax-M3 ~2.7s 可作更快选项

## 📚 引用索引 (references/)

### 核心方法论
- [strategy-adversarial-review.md](references/strategy-adversarial-review.md) — **对抗式审查报告: 第一性原理 + 13因子证伪 + 该留/删/缺失 + P0/P1/P2行动清单** (v5.9 依据)
- [lessons.md](references/lessons.md) — **25 条核心教训** (必读, 含 2026-07-05 新增 23-25)
- [pitfalls.md](references/pitfalls.md) — **17 条 pitfalls 集中索引** (必读, 含并行 max() 评估陷阱)
- [changelog.md](references/changelog.md) — v5.0 ~ v6.0 详细变更
- [architecture.md](references/architecture.md) — 引擎架构 + 因子模型 + v5.0 升级路线图
- [skill-organization.md](references/skill-organization.md) — **Skill 文件结构模式 (可复用)** — SKILL.md INDEX + references/ 分专题

### 执行与输出
- [execution.md](references/execution.md) — 完整执行步骤 + 铁律 + 宽窗口处理
- [output-template.md](references/output-template.md) — LLM 输出模板 + 裁决规则
- [monitoring-claude-code.md](references/monitoring-claude-code.md) — **监控模式: Monitor 工具集成 + 事件协议**
- [prediction-trading-cli.md](references/prediction-trading-cli.md) — **币安预测交易 CLI: 5minbtc_trader.py 用法/参数/安全契约/API端点 (含 --paper/--paper-monitor 模拟)**
- [prediction-market-strategy.md](references/prediction-market-strategy.md) — **预测市场盈利策略: EV=p−P, 价格门控, 凯利仓位, paper 模拟**

### 数据源 & 网络
- [news-sources.md](references/news-sources.md) — 新闻源评估 (清理后只剩 CoinDesk)
- [binance-api-geo.md](references/binance-api-geo.md) — Binance 端点区域问题
- [binance-endpoint-flapping.md](references/binance-endpoint-flapping.md) — 端点双向故障切换
- [high-latency-network-handling.md](references/high-latency-network-handling.md) — 高延迟网络处理 (SSL 超时)
- [polymarket-data-source.md](references/polymarket-data-source.md) — Polymarket 结算源 (Chainlink)

### 引擎专项
- [engine-parallelization-v573.md](references/engine-parallelization-v573.md) — v5.7.3 HTTP 并行化 + positional arg 陷阱
- [black-swan-defense-v571.md](references/black-swan-defense-v571.md) — v5.7.1 黑天鹅防护 (ATR+FNG+news)
- [decel-collapse-pattern.md](references/decel-collapse-pattern.md) — decel 极值崩塌 = V反完成
- [cron-llm-provider-failure.md](references/cron-llm-provider-failure.md) — Cron LLM Provider 失效诊断
- [cron-setup.md](references/cron-setup.md) — Cron Job 配置 + 版本同步
- [dreaming-cron-recovery.md](references/dreaming-cron-recovery.md) — Dreaming Cron 恢复

### 回测 & 复盘
- [backtest-findings.md](references/backtest-findings.md) — 365 天回测深度复盘 + 因子无预测力
- [backtest-v58-1min-findings.md](references/backtest-v58-1min-findings.md) — v5.8 真实 1min 半 K线回测
- [review-procedure.md](references/review-procedure.md) — 每日复盘流程 + 数据质量检查
- [performance-history.md](references/performance-history.md) — 273 笔全量战绩 + 引擎迭代对比

### 单次 session 记录
- [session-2026-06-17.md](references/session-2026-06-17.md) — 5 轮实时预测, v5.7.2 验证
- [session-2026-06-18.md](references/session-2026-06-18.md) — 00:10 mispredict 复盘 → v5.7.4 规则

### 数据采集 & 仓库
- [daily-stock-analysis-data-sources.md](references/daily-stock-analysis-data-sources.md) — daily_stock_analysis 17-fetcher 评估
- [sync-procedure.md](references/sync-procedure.md) — AGI-Super-Team 同步流程
- [quant-knowledge-index.md](references/quant-knowledge-index.md) — 50 轮蒸馏知识库索引

## 复盘记录 (`reviews/`)
按月归档:
```
reviews/
├── 2026-05/  (6 份: review-2026-05-05.md, 24, 25, 27, 27-backtest, 29)
├── 2026-06/  (15 份: 03, 06, 09, 12, 14, 15, 16, 17, 18, 19, 21, 23, 24, 27, 28)
└── 2026-07/  (2 份: 01, 02)
```

## 报告库
14 份深度蒸馏报告在 `reports/` 目录 (也同步在 AGI-Super-Team): R01-R14。

## 与 coin-vp-scanner 的分工

两个都是交易类 skill, **但赌的不是同一件事, 不要混用**:

| | **5minbtc** (本 skill) | [coin-vp-scanner](../coin-vp-scanner/SKILL.md) |
|---|---|---|
| 标的 | **单标的 BTC** | 全量币安 USDT 永续 |
| 周期 | 单根 5min K线 | 1–30min 短线 |
| 核心逻辑 | **真 OFI 净流 + 错价检测** (净流已发生、token 价未定价 → flow-gap) | **确定性结构突破** (放量 + 强实体 + 收盘破 1h 结构位 + 趋势同向, 四条全 ✓) |
| 决策依据 | 概率 `P(close>open\|ofi)` vs 市场 token 价 → `EV = p − P` | 结构规则布尔判定, 非概率 |
| 输出 | 方向 bull/bear + 概率 + edge | 杠杆 / TP / SL 交易卡 |
| 落地方式 | 预测市场 Up/Down token, **仅 paper** (`LIVE_GATE` 硬闸门) | 直接做合约短线 |
| 代码位置 | 本目录自包含 (引擎+脚本+launchd) | 代码在 `~/projects/coin-vp-scanner/`, 本 skill 只是索引 |

**一句话选型**: 要赌"市场定价错了" → 5minbtc; 要抓"价格放量破位了" → coin-vp-scanner。

## 仓库同步
详见 [sync-procedure.md](references/sync-procedure.md)。简述:
```bash
rsync -av --exclude='data/' --exclude='__pycache__/' \
  --exclude='*.jsonl' --exclude='*.jsonl.*' --exclude='*.gz' \
  /home/aa/.hermes/profiles/cqo/skills/5minbtc/ \
  /home/aa/clawd/repos/AGI-Super-Team/skills/5minbtc/
cd /home/aa/clawd/repos/AGI-Super-Team
git add skills/5minbtc/ && git commit -m "sync(skills/5minbtc): <版本>" && git push origin main
```

## 回测系统
```
backtest/
├── fetch_data.py            # Binance 历史数据下载
├── run_backtest.py          # v5.6 回测 (因子无预测力, 公平回测)
├── run_backtest_v57.py      # v5.7 回测 (含前视偏差, 已知)
├── run_backtest_v58.py      # v5.8 回测 (真实 1min 半 K线, 零前视) ← 推荐
├── run.sh                   # 一键运行
├── data/                    # 5min (105K) + 1min (259K) K线
└── results/                 # 回测结果 (gitignore)
```

## 文件结构
```
5minbtc/
├── SKILL.md                      # 本文件 (~170 行 INDEX)
├── 5minbtc-engine-v6.0.py        # 主引擎 (v6.0 真OFI 一票定方向, launchd 调用)
├── 5minbtc-news.py               # 新闻扫描 (CoinDesk RSS, 唯一稳定源)
├── 5minbtc-log.py                # 日志记录 (写入 logs/)
├── archive/                      # 归档
│   └── engines/
│       └── 5minbtc-engine-v5.py  # v5 旧版 (回测因子模块 import)
├── logs/                         # 日志输出
│   ├── 5minbtc-log.jsonl         # 当前活跃 (cron 写入)
│   ├── 5minbtc-log.jsonl.1       # 最新备份
│   └── 5minbtc-log.jsonl.{2..22}.gz  # 历史归档
├── reviews/                      # 每日复盘 (按月归档)
│   ├── 2026-05/  (6 份)
│   ├── 2026-06/  (15 份)
│   └── 2026-07/  (2 份)
├── references/                   # 26 份专项 ref (含 skill-organization 模式)
├── backtest/                     # 回测系统
├── data/                         # 运行时 (news-risk-level.json 等)
├── scripts/                      # 复盘/监控/交易脚本
│   ├── 5minbtc-monitor.py        # ★ 监控脚本 (Claude Code Monitor 集成, v1.0)
│   ├── 5minbtc_watch.py          # ★ Telegram 推送监控 daemon (事件驱动+预测记录+收盘结算)
│   ├── 5minbtc_day_stats.py      # 预测战绩查询 (今日/历史, --push 推送)
│   ├── 5minbtc_trader.py         # ★ 币安预测交易桥接 (--once/--loop/--monitor/--paper/--paper-monitor)
│   ├── prediction_ws_feed.py     # 币安 w3w-prediction WS 实时价源 (<200ms)
│   ├── ofi_feed.py               # ★ 真订单流采集 (trade+bookTicker tick规则, launchd com.daniel.ofi-feed)
│   ├── 5minbtc_keyless_paper.py  # 免密钥模拟盘 (公开BTC数据模拟UP/DOWN价)
│   ├── telegram_push.py          # 通用 Telegram 推送助手
│   ├── daily-review-stats.py
│   └── fetch-github-repo.sh
14. 🔴 高延迟网络 — 引擎timeout临时修补 (2026-06-24)
15. 🔴 Web搜索不可用时的降级策略
16. 🔴 并行工具调用延迟评估 = max() not sum() (2026-07-05)
17. 🔴 SKILL.md 维护: 定期重构为 INDEX 风格 (2026-07-05)

---
最后更新: 2026-09-10 — 引擎 v5.7→**v6.0** 改名 (文件/SKILL/引用全线对齐, 修引擎内"无中性"过期注释) + SKILL.md 版本刷到 6.0.0 + 性能快照改为审查后的诚实口径 + 补 v5.9/v5.10/v6.0 changelog + 新增与 coin-vp-scanner 的分工说明
