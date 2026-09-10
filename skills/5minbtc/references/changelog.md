# 5minbtc 版本变更日志

> 详细 changelog。SKILL.md 只保留当前版本亮点。
>
> 版本号分两条线：**引擎文件内的 docstring 版本**与**策略版本**曾长期脱节（文件名 `-v5.7.py` 里跑的是 v6.0 代码），v6.0.0 起已对齐。

## v6.0.0 变更 (2026-08-18, commit e893d31) — 真 OFI 驱动: 方向一票交给订单流

**背景**：v5.9 的对抗式审查已经证明"方向预测"没有 alpha（bear 50.0% = 纯硬币，non-neutral 57.7%）。
v6.0 不再假装能预测方向，改为**检测错价**：真 OFI 净流方向 = 真实资金流方向，
若净流已经发生、而 UP/DOWN token 价还没跟上，中间那段 gap 才是真正的钱。

| 变更项 | 详情 |
|--------|------|
| **方向判定** | `ofi_direction()`: bias 由**真 OFI 净流一票决定**（`ofi_n>0`→bull / `<0`→bear），替代 v5.10 的 `body>0→bull` 纯延续统计。**二选一无中性**；`ofi_n` 缺失/为 0 时用 body 符号兜底并标 `meta.body_fallback`（弱信号/流量不足只让概率趋近 0.5 → EV 过滤不下单，不产生 neutral） |
| **OFI 主源** | 当前 K 线**原生 in-candle** `ofi_n = 2*(tb/v) − 1` ∈ [−1,1] — 取 REST `klines[9]`（taker buy base volume）做原生 aggressor 聚合，**天然按 K 线对齐，零 WS 依赖** |
| **OFI 辅源** | WS `~/bb-auto/ofi.json`（`ofi_candle` / `ofi_60`）用于**新鲜度反转保护**与交叉校准；`load_ofi()` 新增 **ts 保鲜校验**（age > 30s → `feed_fresh=False`，WS 分量自动降级，引擎只信 REST 主源） |
| **概率** | `ofi_probability()`: `confidence = P(close>open \| ofi)`，替代 `close_direction_confidence()` 的延续概率。三层 = ① 经验校准表（按 `ofi_n` 分桶 + **Bayesian shrink**，`OFI_BAYES_N=30` 向 0.5 收缩）② flow-gap（净流已发生但价格未定价）③ 最近 60s 流（按剩余时间衰减） |
| **edge** | 改为**错价检测** `EV = p − ask`（真 OFI 概率 vs token 市场价），由 `5minbtc_realtime.py` 执行 |
| **风控** | realtime 新增 **D2 有效性闸**：滚动 200 笔已结算 OFI 方向胜率 < 0.55 → 自动暂停 + 告警（防第二次 52.6%） |
| **保留** | ATR spike / FNG<25 / news 黑天鹅断路器；MTF 4h **只降权不翻方向**；EV 下单框架；**13 因子仍计算并输出，但不再参与 bias** |
| **门限** | `T_OFI_GATE=0.20` / `T_OFI_60=0.35` / WS 质量闸 `OFI_CR_MIN=0.80` |

**契约**：输出 `"version": "6.0.0"`，`factors` / `score` 字段保留（仅作 `strength` 标签与 LLM 参考）。

**命名修正**：引擎文件自本版起为 `5minbtc-engine-v6.0.py`。此前文件名为 `5minbtc-engine-v5.7.py`，与其中运行的 v6.0 代码完全脱节——`scripts/*.py` 的 `ENGINE` 常量、`SKILL.md`、`README.md`、`references/` 中的引用已全量更新。
⚠️ 注意：由此产生一个副作用——`references/` 里的**历史文档**（pitfalls / binance-api-geo / high-latency 等）中的旧文件名也被一并替换为 v6.0，阅读时请知悉那些命令当时对应的其实是旧名文件。

## v5.10.0 变更 (2026-08-17, commit 50a4815) — 概率套利策略 + pnl 修复 + 时段过滤

**从"猜方向"转向"比价格"的转折点** —— 第一次把引擎输出当成概率去和市场报价比较。

| 变更项 | 详情 |
|--------|------|
| 方向去中性 | 删掉 `neutral` 阈值分支（原 v5.5 的 `[-1,1]` 中性区），改为 `bias = "bull" if body > 0 else "bear"` **二选一**，方向由半 K 线 body 决定 |
| 概率字段 | `prediction` 新增 `probability = round(confidence/100, 3)`（此时仍为 v5.9.2 的**半 K 线延续概率**） |
| 概率套利 | realtime: 引擎概率 > 市场 ask + `min-edge(0.03)` → 买（`EV = p − P > 0`）；否则无 edge 跳过 |
| 时段过滤 | 新增 `--active-hours`（默认 `20,21,22,23`）——只在历史高胜率时段下单 |
| pnl 修复 | 输单应亏**全额** `-amount`，此前错算为"亏入场价 `-amount*ask`"（系统性低估亏损） |
| 稳定性 | 崩溃循环修复 + 台账去重 + 精简推送 |

## v5.9.0 变更 (2026-08-13) — 对抗式审查重构: 13 因子收敛到 3 信号

**依据**：[strategy-adversarial-review.md](strategy-adversarial-review.md)（5 位对抗审查专家的结论综合）。核心结论——**方向准确率不是 edge，`EV = p − P − 成本` 才是**。

| 变更项 | 详情 |
|--------|------|
| 因子证伪 | 公平回测显示 13 个因子里 **11 个只有 47–49%**（等同抛硬币），其中 `momentum` 48.1%、`rsi` 47.3% **反向**；唯一有独立 alpha 的是 `volume` 58.1%，而它权重只有 0.3 —— **权重与证据完全倒挂** |
| 权重收敛 | `BASE_W` 中 10 个因子清零，只留 `half_body 1.2`（延续主信号）+ `volume 0.8`（唯一独立 alpha）+ `meanrev 0.3`（唯一正向价格因子 51.7%）；未验证的 `taker_buy` 也清零 |
| 新增三层过滤 | ① **多周期结构** 4h/1h/15m（linreg slope + ADX + %B）② **跨资产广度** ETH/SOL 5m 动量（趋势日逆势信号打折）③ **真订单流 OFI** |
| 移除 | `bull×0.92` 惩罚、Platt 置信度门控（v5.5 引入，被证为反校准） |
| v5.9.2 | 收盘方向置信度改用**半 K 线延续概率**（`close_direction_confidence`），替代 Platt Scaling |

**认知转变**：从前视偏差回测的 71.2% 幻觉中退出——零前视 v5.8 只有前 2 根 1min 61.4%，且 61–70% 是"看着 K 线走完再确认"的延续性，做市商早已定价进 token 价。

## v5.8.0 变更 (2026-08-11) — 主动买量因子 + 订单簿多时刻去噪

**量能/订单簿信号质量升级 — 对齐 OFI 路线图的第一步**

| 变更项 | 详情 | 效果 |
|--------|------|------|
| `taker_buy` 因子 (因子13) | `fetch_klines` 解析 Binance klines 索引9 (taker buy base volume)，新增 `tb` 字段；`taker_buy_signal()` 取最近5根已完成K线 tb/v 占比均值映射 [-1,1] | 区分主动买/主动卖，替代「投影放量」的近似。`tb=0` 是有效信号(全主动卖)不跳过；`tb>v` 容错钳制 |
| 权重接线 | BASE_W 加 `taker_buy=0.7`，REGIME_ADJ 各 regime 对应加值；`combine_factors` 动态查权重自动计入 score | 新因子立即生效，无需硬编码白名单 |
| `fetch_depth_avg` 多时刻采样 | 订单簿 3 次采样 ×1s，同价位 bids/asks 按量平均合并；单次失败跳过，全失败返回 None | 降低单次快照的瞬时报单噪声。合并结果按 limit 截断避免层数膨胀 |
| 契约保持 | `prediction` 子对象结构不变，version → 5.8.0 | 监控脚本零改动兼容 |

**关键 pitfall (测试暴露)**: 初始实现用 `v>0 and tb>0` 守卫，把 `tb=0` 当作「无数据跳过」——但实盘 `tb=0` 是强信号(主动买量为零=全主动卖)，被误跳过会导致看空信号丢失。已改为「tb 字段缺失才跳过」。

**验证**: `scripts/test_engine_v58.py` 12 项测试 (契约/数值/多时刻采样/稳定性) 全绿。



## v5.7.4 变更 (2026-06-18) — TREND强趋势decel极值约束


**2026-06-18 00:10 candle mispredict复盘驱动**

| 变更项 | 详情 | 根因 |
|--------|------|------|
| TREND decel约束 | EMA delta>$100的强TREND中，\|decel\|>0.7必须配合\|half_body\|>0.15同向才可翻转方向 | 00:10 candle: EMA delta=+$188, decel=-0.801, half_body=+0.009十字星, engine=neutral。LLM基于decel+position覆盖bear→实盘收涨❌。强趋势中decel减速是正常呼吸，十字星=空方无力 |
| LLM覆盖纪律 | engine=neutral/weak(score≈0)且regime=TREND时，decel极值不能单独作为方向翻转依据 | 仅decel+position在强TREND中是不够的——需要half_body实体确认 |

**关键洞察**: decel测量的是价格变化率的变化——在强趋势中，短暂减速后继续同向是常态而非反转。仅当half_body确认实际方向已改变(实体>ATR×0.15)时，decel极值才构成有效反转信号。



## v5.7.3 变更 (2026-06-17) — 引擎HTTP并行化


**用户反馈"预测太慢"→引擎4路并行HTTP提速 4-5x**

| 变更项 | 详情 | 效果 |
|--------|------|------|
| ThreadPoolExecutor(max_workers=4) | 4个HTTP调用(klines+depth+FNG+chainlink)并行发射 | 引擎12-18s→~3.0s |
| `_fetch_fng()` 独立函数 | 并行化需要picklable的函数引用 | 不破坏原有逻辑 |
| 全链路提速 | 引擎+新闻+搜索并行→全链路~7s | 之前22-29s，提速~3x |

**关键pitfall**: `ex.submit(fetch_klines, 200)` 把 `200` 传给第一个参数 `symbol`→HTTP 400。必须用 `ex.submit(fetch_klines, limit=200)`。

详见 `references/engine-parallelization-v573.md`。



## v5.7 变更 (2026-05-28)


**核心策略变更: 在K线第4分钟执行(progress~80%)，利用前半根K线实体方向确认延续**

设计思路(Daniel提出): 实盘66%准确率的edge来自"确认当前K线已有走势"(progress=0.9+)，v5.7把这个隐性优势显性化。

| 变更项 | 详情 | 效果 |
|--------|------|------|
| S1 `half_body_momentum()` | 新因子，progress≥0.45时激活，ATR归一化实体+tanh压缩 | 将实盘edge显性建模 |
| S2 ATR乘数×0.55 | pred_close乘数 0.20/0.12→0.11/0.066 | 只预测剩余~2.5分钟 |
| S3 half_range缩窄 | 0.65→0.40 | 区间更紧凑 |
| Cron调度 | 第2分钟执行(`2,7,12...`) | progress~40%，前2根1min构建半K线 |
| `BASE_W['half_body']=1.2` | 所有因子中最高权重 | 核心edge因子 |
| `REGIME_ADJ` 更新 | 所有4个regime添加half_body权重 | regime-aware调整 |

`half_body_momentum()` 关键设计:
- 激活阈值: progress≥0.45 (给K线足够时间形成实体)
- 进度加权: `min(1.0, (progress-0.3)/0.7)` — 0.45→0.2, 0.8→0.71, 1.0→1.0
- ATR归一化: body/ATR → tanh(×2.0) → [-1, 1]
- progress<0.45时返回0.0 (不干扰其他因子)



## v5.8 回测方法论突破 (2026-05-28)


**关键改进: 用真实1分钟K线构建半K线状态，零前视偏差**

之前v5.7回测用 `(open+actual_close)/2` 模拟中点→71.2%但含前视偏差；用前一根5min body→48.1%无预测力。
**正确方法(Daniel提出)**: 用对应5min K线的前2-3根真实1分钟K线的OHLCV构建半程状态。

回测结果(半年, 27,237轮方向性):

| 前1根1min (20%) | 前2根 (40%) | 前3根 (60%) | 前4根 (80%) | 前5根 (100%) |
|:---:|:---:|:---:|:---:|:---:|
| 56.7% | **61.4%** | 65.8% | 69.5% | 76.1% |

核心发现:
1. 半K线延续性是真正的alpha来源 — 越接近完成越准，近似线性增长
2. 前2根(当前cron配置): 27,237轮→61.4%, edge +11.4pp, 最长连胜22
3. half_body因子方向准确率仅48.5% — alpha不在因子本身，在于触发了更紧的ATR阈值
4. volume是唯一有独立预测力的因子(56-58%)，其他因子全部49-51%
5. 之前的实盘66%准确率谜团已解开 — 就是半K线延续性效应

回测文件: `backtest/run_backtest_v58.py` (数据: `backtest/data/btcusdt_1m.json`, 259k根)
用法: `python3 run_backtest_v58.py --fast --compare` 或 `--half 3` (前3根1min)



## v5.6 变更 (2026-05-27)


基于3次方向错误深度复盘的4项修复（已实施验证）：

| 修复项 | 变更 | 根因 |
|--------|------|------|
| R1 momentum/decel冲突检测 | \|mom\|>0.7且\|decel\|>0.8且方向相反时，动态降权mom 1.0→0.4, 升权decel 0.7→0.9 | V型反转点momentum锁定错误方向 |
| R2 V型反转因子 | `v_reversal_detect()` 检测低点抬高模式 [-1,1], BASE_W=0.8 | 捕捉结构性的反转信号 |
| R3 放量突破因子 | `vol_breakout_signal()` 用最近3根完整K线的最大量K线方向 [-1,1], BASE_W=0.4 | 避免未完成K线的量价误导 |
| R4 Chainlink价格对齐 | `fetch_chainlink_ref()` Coinbase BTC-USD作参考，自动补偿Binance偏移 | Polymarket结算价≠Binance价格 |

关键代码模式：
- **冲突降权用saved_base模式**: `saved_base = BASE_W.copy()` → 临时改权重 → `combine_factors()` → `BASE_W.update(saved_base)` 恢复。避免跨调用污染全局权重。
- **Chainlink偏移安全边界**: |offset|>300时不补偿（防止API异常导致预测价飞出合理范围）
- **V反转用已完成K线**: 取 `candles[-4:-1]`（最近3根完成K线），不用当前未完成K线
- **输出新增字段**: `chainlink_offset` 追踪每次偏移量, `v_reversal`/`vol_breakout` 因子值



## v5.5 变更 (2026-05-26)


基于120轮v5.4实战复盘的4项优化：

| 优先级 | 修复项 | 变更 | 影响 |
|--------|--------|------|------|
| P0-1 | 置信度校准 | `40+abs(score)` → Platt Scaling sigmoid | conf与准确率正相关 |
| P0-2 | 新闻因子 | 98% NEUTRAL死代码，保留扫描给LLM | 减少噪声 |
| P1-1 | Bull bias | score>0时×0.92衰减 | bear 70.2% > bull 65.4%修正 |
| P1-2 | 高vol惩罚 | HIGH_VOL 0.6→0.45 | 放量准确率更低 |

附加优化：
- neutral区收缩 [-2,2]→[-1,1]，减少无信息预测
- 置信度上限 80→85，让强信号有区分度
- `calibrate_confidence()` 独立函数，midpoint=15, steepness=0.10



