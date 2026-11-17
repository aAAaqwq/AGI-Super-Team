# 持仓「回本要多久」测算

**用途**：用户被套后问「反弹回成本线要多久」「还有救吗」。这是**决策题**，不是数学题。

---

## 一、先纠正两个认知错误

### ① 亏损与回本不是线性关系

```
回本需涨% = 成本 / 现价 − 1
```
- 跌 30% → 需涨 **+42.9%**
- 跌 20% → 需涨 **+25.0%**
- 跌 50% → 需涨 **+100%**

**永远不要用跌幅反推涨幅。** 用户说「只跌了 30%」，要立刻换算成「得涨 43%」。

### ② ⭐ 中位数是幸存者偏差（最大的坑）

统计「历史上从任一起点涨到 +X% 要多久」时，**中位数只统计了成功到达的样本**，完全掩盖了「大量样本根本到不了」这件事。

**必须报三件套**：
```
需涨 X%  |  历史中位 N 个交易日  |  250日内达成率 Y%
```

---

## 二、算法

对近 250 个交易日的**每一个交易日**作为起点：

1. 取该日起点收盘价 `c[i]`
2. 目标价 = `c[i] * (1 + required)`
3. 向后扫描最多 250 天，找首次 `high[j] >= 目标价` 的 j
4. 记录耗时 `j - i`；找不到则计为「未达成」
5. 输出：**达成率**（有多少起点最终达成）+ **耗时分位数**（只在达成样本内计算：p25 / 中位 / p75 / p90）

```python
import urllib.request, json, statistics as st

def fetch(u, t=30, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(u, headers={"User-Agent":"Mozilla/5.0"}), timeout=t
            ).read().decode('utf-8','ignore')
        except Exception:
            if i == tries-1: raise
            import time; time.sleep(1)

def load_kline(code, n=300):
    """code 形如 sz000001 / sh000003；腾讯前复权日K"""
    k = json.loads(fetch(
        f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{n},qfq"))
    rows = k['data'][code].get('qfqday') or k['data'][code].get('day')
    close = [float(r[2]) for r in rows]
    high  = [float(r[3]) for r in rows]
    return close, high

def breakeven_stats(code, cost, horizon=250):
    close, high = load_kline(code)
    px = close[-1]
    required = cost/px - 1
    spans, miss = [], 0
    for i in range(max(0, len(close)-horizon)):
        target = close[i] * (1 + required)
        hit = None
        for j in range(i+1, min(i+horizon+1, len(high))):
            if high[j] >= target:
                hit = j - i
                break
        if hit is None:
            miss += 1
        else:
            spans.append(hit)
    total = len(spans) + miss
    if not spans:
        return {"px": px, "required": required, "achieve_rate": 0.0, "median": None}
    spans.sort()
    q = lambda p: spans[min(len(spans)-1, int(len(spans)*p))]
    return {
        "px": px,
        "required": required,
        "achieve_rate": len(spans)/total,
        "median": st.median(spans),
        "p25": q(.25), "p75": q(.75), "p90": q(.90),
        "fastest": spans[0],
        "sample_ok": len(spans), "sample_all": total,
    }
```

---

## 三、实测数据（2026-10-19，示例持仓）

| 股票 | 成本 | 现价 | 需涨 | 中位耗时 | 250日达成率 | 结论 |
|---|---|---|---|---|---|---|
| **示例股E** 000004 | 28.55 | 26.95 | **+5.94%** | **14 日（约 3 周）** | **94%** | 🟢 值得等 |
| **示例股G** 000003 | 3.66 | 2.95 | **+24.07%** | 26 日（约 5 周） | **40%** | 🔴 反抽就走 |
| **示例股C** 000003 | 12.90 | 8.93 | **+44.46%** | 20 日（约 4 周） | **31%** | 🔴🔴 别等 |

### 关键读法

- **示例股C**：中位 20 天看着很快，但达成率仅 31% —— **「看起来快」的制度性欺骗**。它是妖股（近 250 日涨停 23 次、5 日最好 +61.78%），成功时极快、失败时一年都不动，**双峰分布，中位数毫无代表性**。
- **示例股E**：达成率 94%，中位 3 周 —— **这才是真正的"等得起"**。
- **示例股G**：40% 达成率 + 均线全破 —— 典型尴尬区间。

### 补充：波动能力（判断"有没有可能"）

同时统计该股「近 250 日涨停次数」和「5 日最大涨幅」：
- 5 日最好 +61.78%（示例股C）→ **有能力**短期暴拉，但取决于是否有新逻辑
- 5 日最好 +27.17%（示例股E）→ 温和
- 若近 250 日涨停 0 次 → 基本不可能短期 +40%

**有波动能力 ≠ 会涨。** 只说明"够得着"，不说明"会去够"。

---

## 四、输出话术（用户是短线交易者，要直白）

### 必须讲清的三层成本

| 成本 | 说法 |
|---|---|
| **时间成本** | 「达成率只有 31%，意思是 100 次里 69 次一年都等不到」 |
| **机会成本** | 「同样的钱换到有人做的品种上，3 个月可能 +10-20%」 |
| **心理成本** | 「每天看它跌，容易在最低点割肉 —— 这是最坏的结局」 |

### 结论句式

> **「关键不是哪个赚更多，是你愿不愿意用 1 年时间赌那 20%。」**

### 不要一刀切

用户**明确不接受一次性清仓**（会讨价还价「真得完全割吗」）。给**分批 + 死线**：

```
留 X% → 反抽到 A 减半 → 破 B 全清
```

并明确「保留的是"最后一张彩票"，不是"等回本"」——**把"回本"这个念头和他分开**，让他决策的是「这笔钱放在这里值不值」。

---

## 五、Pitfalls

- **只报中位数 = 骗人**。必须带达成率，否则用户会按"20 天就能回本"做决策。
- **样本量必须披露**：单只股票 250 天 = 250 个起点，`sample_all` 要报出来；不足 120 天时数据不可信。
- **前复权 vs 不复权**：用 `qfq`（前复权），否则除权日会造成假跳空，把历史高点算错。
- **不要用「跌幅」类比同类股**：每只票的波动结构不同（妖股 vs 蓝筹），达成率差异极大。
- **回本测算不能替代趋势判断**：达成率高但趋势坏（均线全破）的票，仍然该走。**测算是"能不能等到"，趋势是"该不该等"。**
- **ETF 不适用**：宽基 ETF 用「回撤分档 + 持有期胜率」另一套方法（见 `ashare-stock-research/references/index-etf-risk-return.md`），不是回本测算。
