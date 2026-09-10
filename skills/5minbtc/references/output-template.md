# 5minbtc 输出模板

> ⚠️ **本文件是 2026-09-10 补写的。** 此前 `SKILL.md` 与 `execution.md` 都引用它（"LLM 输出模板见 output-template.md"），
> 但**这个文件从未存在过** —— 也就是说"LLM 该输出成什么样"从来没有书面规范，只有代码里的推送格式。
> 本文件把**实际在跑的格式**（从代码逐条抄出）与**新拟的 LLM 输出模板**分开标注，不要把两者混为一谈。

## 0. 三个输出面（不要混）

| 输出面 | 谁生成 | 能否手改 |
|--------|--------|---------|
| **系统推送** | `realtime` / `watch` / `trader` 的 f-string | ❌ 改代码才变；本文只做记录 |
| **LLM 综合报告** | 你 / LLM 按 §5 模板写 | ✅ 这是本文件存在的意义 |
| **日志写入** | `5minbtc-log.py` 追加 jsonl | 固定 8 个参数，见 `execution.md` |

---

## 1. realtime 推送（5 秒刷新，系统自动）

> 代码：`scripts/5minbtc_realtime.py` · 全部硬编码 f-string，**没有配置文件**

### 1.1 每根 K 线的预测快照 ← 最常收到的那条

`fmt_prediction()` L327：

```
📊 预测 {方向中文} | {K线起始} p{进度}%
概率 {该腿概率} | 市场 {UP|DOWN} {ask} | edge {±差值}
→ {动作}
[上一轮 {时间} {方向} → {收阳|收阴} ✅|❌]
```

字段语义（这几条不看代码猜不出来）：

| 字段 | 含义 |
|------|------|
| `p4%` | **K 线进度**百分比，**不是概率** |
| `概率 0.59` | **该腿**的概率：UP 腿 = `P(close>open)`；DOWN 腿 = `1 − P` |
| `edge -0.07` | `该腿概率 − 该腿 ask`（负 = 无套利空间） |
| `→ …` | 四种动作之一（下表） |
| `上一轮 …` | 上一根 K 线的方向 vs 实际收盘，仅在有跨轮状态时出现 |

`→` 后的动作与判定顺序（L457-464）：

| 动作 | 条件 |
|------|------|
| `非活跃时段` | 当前小时 ∉ `--active-hours`（默认 `20,21,22,23`） |
| `市场价不可用` | 取不到该腿 ask |
| `🎯 下单` | `edge ≥ --min-edge`（默认 `0.05`） |
| `⏭️ 跳过(无edge)` | 其余 |

### 1.2 其余存活格式

| 触发 | 函数 | 格式 |
|------|------|------|
| 下单成交 | `fmt_order()` L315 | `🎯 真OFI·下单 \| {方向}` / `{K线} \| {side} @ {ask} \| 1U` / `概率 … vs 市场 … \| edge … \| 已记录` |
| 结算 | inline L262 | `🏁 结算 {时间} {side} ✅中\|❌未中` + `买入 …U @… \| 涨跌 …% \| PnL …$` + 账户块 |
| 限价未成交 | inline L289 | `❌ 未成交 \| {时间} {side} 限价… 收盘未触及` + 账户块 |
| 有效性闸 | inline L483 | `⛔ OFI有效性闸触发: {n}笔 OFI 方向胜率 {x}% < {阈值} → 暂停下单`（1h 节流） |

### 1.3 已删除 / 仍残留的死代码

**已于 2026-09-10 删除**（按最小无用原则，均无调用点；需要时从 git 历史取回）：

| 函数 | 原属功能 |
|------|---------|
| `record_limit()` / `fmt_limit()` / `fmt_skip_knife()` | 「甜区限价挂单」—— 已确认废弃。`record_limit` 是该功能唯一的 pending 单产生方 |
| `fmt_no_edge()` / `fmt_signal()` | 已被 v5.10 起的 inline action 文案取代 |

**仍残留（未删，等你确认）**：

| 位置 | 为什么是死的 |
|------|-------------|
| `bias == "neutral"` 分支（`🧭 预测 中性…`） | v6.0 `ofi_direction()` **二选一无中性**，该分支不可达 |
| `watch.py` 里 `CLEAR-SIGNAL` 的 `bias != "neutral"` 判断 | 同上，该条件恒为真 |

> ⚠️ **不要连带删** `realtime` 的 pending 单结算段（`status == "pending"` 的处理）：
> `record_limit` 虽已删，但 `5minbtc_keyless_paper.py` 与历史台账仍会产生/存在 pending 单。
>
> 教训：改推送格式时**先 grep 调用点**再改，否则会改到不存在的路径上。

### 1.4 ⚠️ 快照里的概率在 K 线开局阶段不可信

每根 K 线的**第一秒** realtime 就会推一条 `p1%` 快照，但那个概率是从刚开几秒的成交里算出来的：

- 主源 `ofi_n = 2*(tb/v)−1` 取**进行中** K 线，`_ofi_native()` 只挡 `v<=0`，**无最小样本量保护**
- `vol_gate`（本该拦这个的闸门）**算了不用** —— 详见 [pitfalls.md #18](pitfalls.md)
- 实测：某根 K 线开局 3.4 BTC（均量 39.85 的 8.5%）就能得到 `ofi_n = +0.87`

**因此**：

| 进度 | 怎么看待这条快照 |
|------|----------------|
| `< 20%` | **不要当信号**。只说明"盘口在动"，概率/edge 一律标注数据不足 |
| `20–40%` | 谨慎参考，仍以观察为主 |
| `≥ 40%` | 可采信（日志里 99.7% 的已验证样本都在 40–60% 这个区间） |

引用概率时**必须带上进度**，别把 `p1%` 的 0.70 和 `p45%` 的 0.70 当成一回事。

---

## 2. watch 事件推送（事件驱动 + 每小时心跳）

> 代码：`scripts/5minbtc_watch.py` · 采样分钟 `SAMPLE_MINUTES=(2,3,4)`，秒 `+5`

### 2.1 通用事件体

`fmt_event(tag, d)` L244：

```
{emoji} [5minbtc] {tag} {K线ISO} p{进度}%
方向: {方向中文} ({strength}) | 置信 {confidence}
现价 {当前价} | 预测收 {pred_close} (低{pred_low}/高{pred_high})
regime {regime}[ | FNG {value} {label}][ | 买力 tb={±}]
[信号源: {多周期/跨资产/OFI 一行}]
[tag==CLEAR-SIGNAL → "⚠️ 达到明确信号门槛 — 人工复核后再考虑动作, 非投资建议"]
[black_swan_warning → "🚨 黑天鹅警告: 方向不可靠"]
── 预测市场 ──
{盘口 + 模拟持仓}
```

- `emoji`：`bull 🟢 / neutral ⚪ / bear 🔴`
- `信号源` 行由 `_mtf_line()` 生成（4h 斜率 / 1h ADX / 15m %B / ETH+SOL 广度 / OFI）
- 盘口块 `market_line()`：真实价优先，取不到则标 `(模拟)`，再取不到标 `(不可用)`；后接模拟持仓

### 2.2 tag 与触发条件

| tag | 触发 |
|-----|------|
| `START` | 首次采样（`last_bias is None`） |
| `DIR-CHANGE` | `bias` 相对上一次变化 |
| `CLEAR-SIGNAL` | `bias != "neutral"` 且 `strength ∈ {medium,moderate,strong}` 且 `confidence ≥ --min-conf`（默认 50） |
| `TB-FLIP` | `taker_buy` 正负号翻转 |
| `PREDICT` | 仅 `--every-candle` 时 |
| `心跳` | 每 `--heartbeat` 秒（默认 3600） |
| `引擎采样失败 xN` | 连续失败第 1/3/6/10 次各推一次 |

> ⚠️ `CLEAR-SIGNAL` 的 `bias != "neutral"` 判断在 v6.0 下**恒为真**（引擎无中性）—— 与 §1.3 同源的遗留。
> 另：生产环境 `5minbtc-watch` 用 `--mute` 启动，**事件推送整体关闭**，只保留预测记录 + 结算 + 每日战绩；
> 事件推送实际由 realtime 承担。调试时才去掉 `--mute`。

---

## 3. trader（paper 模拟盘）

> 代码：`scripts/5minbtc_trader.py --paper-monitor` · 由 `com.daniel.5minbtc-paper` 守护

| 触发 | 格式 |
|------|------|
| 账户总览 | `📊 5minbtc 预测市场 Paper 模拟` + 注单统计 + 胜率 + `账户: $100 → $xx.xx (+x.xx%)` + 最近 5 笔 |
| 结算 | `🏁 模拟结算{时间} {side} @{ask} ✅\|❌` |
| 账户变动 | `💼 模拟账户${br} → ${equity}` |
| 成交 | `✅ 模拟成交 \| {时间} {tag} UP` |
| 第 3 分钟预测 | `🔎 第3分钟预测(模拟) \| {时间} …` |
| 未成交 | `❌ 未成交 \| {时间} {side}` |
| 挂单/盯盘 | `📡 模拟{side} @{ask} → 现价 {cur}` |

---

## 4. 每日战绩

> `scripts/5minbtc_day_stats.py --push`，由 watch 在跨日时自动触发

```
📈 5minbtc 预测战绩 | {日期}
━━━━━━━━━━━━━━━━━━━━
记录预测 N 条
已结算 M 条 | 方向命中 x/M = P%
收盘在预测区间 y/M = P%
MAE z% | 方向分布 {…}
━━━━━━━━━━━━━━━━━━━━
最近结算: …
```

---

## 5. LLM 综合报告模板

> 🆕 **本模板是本次新拟的**，此前不存在书面版本。它必须与 v6.0 的现实一致：
> **方向由 OFI 一票决定，不再由因子打分** —— 所以报告里不要再出现"因子打分/13 因子"的推理链。
> 铁律：输出 **15–25 行**（`SKILL.md` 铁律 #5）。

```
📊 BTC 5min | {K线时间} | p{进度}%

方向: {看多/看空} ({strength}) | 概率 {P(该腿)} | 置信 {confidence}
现价 {current} | 预测收 {pred_close} ({pred_low}–{pred_high})
regime {regime} | FNG {value} {label}

【为什么】
· OFI: ofi_n={±x.xx} ({净流入/流出}) | flow-gap {±x.xx} | 校准概率 {p_cal} (n={cal_n})
· 过滤: 4h {↑/↓/—} | 1h ADX {x} | 15m %B {x} | ETH/SOL 广度 {±x}
· [反向保护] {reversed_60 / ws_conflict 时说明}
   ⚠️ 不要写"流量不足所以概率不可信"—— `vol_gate=false` 时引擎**不会**降低概率，
      它只是个装饰字段（见 §1.4）
· 新闻: {3 组搜索结果一句话结论}

【市场】
· UP {x.xx} / DOWN {x.xx} | 我买 {UP/DOWN} @ {ask}
· edge = {p_side} − {ask} = {±x.xx} → {下单 / 跳过 / 非活跃时段}

【风险】
· {黑天鹅警告 / ATR spike / 流量不足 / 无}

⚠️ 非投资建议, 仅量化研究
```

填写纪律：

1. **方向必须与引擎一致**。bias 是 OFI 一票决定的；只有在 `meta.body_fallback=True` 或 OFI 数据缺失时才可以改，且必须写明原因（见 `SKILL.md` 铁律 #4）。
2. **概率要写清是哪条腿**：UP = `P(close>open)`，DOWN = `1 − P`。写错方向会让整篇报告反向。
3. `edge` 为负就明确说"跳过"，不要用"倾向"这类模糊词掩盖没有套利空间的事实。
4. 超出单根 K 线窗口的提问（"今晚涨跌"）按 `execution.md` 处理：给倾向 + 标注"超出引擎置信区间"。
5. 有 `black_swan_warning` 时，方向结论必须标注不可靠。
