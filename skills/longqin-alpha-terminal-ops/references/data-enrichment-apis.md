# 东财 / 腾讯 财务数据接口（实测可用性，2026-10-28）

做「基本面快筛」（营收增速 / 净利 / 毛利率 / ROE / PB）时踩过的接口坑。**只记实测结论，别浪费时间在坏接口上。**

---

## ✅ 唯一推荐：`RPT_LICO_FN_CPD`（业绩报表）

```python
import urllib.request, json, urllib.parse

def fetch(u, t=25):
    return urllib.request.urlopen(urllib.request.Request(
        u, headers={"User-Agent":"Mozilla/5.0","Referer":"https://data.eastmoney.com/"}),
        timeout=t).read().decode('utf-8','ignore')

u = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD"
     "&columns=ALL&filter=" + urllib.parse.quote('(SECURITY_CODE="600698")') +
     "&pageNumber=1&pageSize=6&sortTypes=-1&sortColumns=REPORTDATE&source=WEB&client=WEB")
rows = ((json.loads(fetch(u)).get('result') or {}).get('data') or [])
```

**字段**：

| 字段 | 含义 | 说明 |
|---|---|---|
| `REPORTDATE` | 报告期 | `2026-06-30` |
| `TOTAL_OPERATE_INCOME` | 营业总收入 | **除以 1e8 得亿元** |
| `YSTZ` | 营收同比 % | 直接读 |
| `PARENT_NETPROFIT` | 归母净利 | 除以 1e8 |
| `SJLTZ` | 净利同比 % | 直接读 |
| `XSMLL` | 毛利率 % | 直接读 |
| `WEIGHTAVG_ROE` | 加权 ROE % | 直接读 |

**优点**：稳定、字段名统一、一次给 6 期、对亏损股也返回（`SJLTZ` 可能是 −860.50 这种极端值）。

---

## ❌ 坏接口（别再试）

| 接口 | 症状 | 结论 |
|---|---|---|
| `RPT_F10_FINANCE_MAINFINADATA` | 返回 6 条记录但**所有字段都是 `None`**，格式化后全变 `-` | 字段名/口径不匹配，**弃用** |
| `emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/MainTargetAjax?type=0&code=SH600698` | 先报 `Unexpected UTF-8 BOM`；改用 `utf-8-sig` 后返回空/HTML → `Expecting value: line 1 column 1` | **弃用** |
| 腾讯 `web.ifzq.gtimg.cn/appstock/app/StockData/stockFinancial` | `{"code":11,"msg":"Can't load controller:StockDataController"}` | **弃用** |
| 新浪 `money.finance.sina.com.cn/corp/go.php/vFD_FinanceSummary/stockid/600698.phtml` | 返回 HTML，正则提取不稳 | 不推荐 |

**注意**：`RPT_F10_FINANCE_MAINFINADATA` 这类 F10 接口失败时**不会报错**，只会静默返回 `None`。
如果看到「营收/净利/毛利率全是 `-`」，先怀疑接口选错，不要怀疑股票没数据。

---

## 配套：股东户数（筹码集中度）

```python
u = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_HOLDERNUM_DET"
     "&columns=ALL&sortColumns=END_DATE&sortTypes=-1&pageNumber=1&pageSize=4"
     "&filter=" + urllib.parse.quote('(SECURITY_CODE="600698")') + "&source=WEB&client=WEB")
# 字段：END_DATE / HOLDER_NUM / HOLDER_NUM_RATIO / AVG_HOLD_AMT
```

**判据**：`HOLDER_NUM_RATIO` 近 1-2 期减少/持平 → 筹码集中；**单期 +30% 以上 → 直接剔除**（散户接盘）。

**注意**：有些股票的户数数据严重滞后（实测湖南天雁最新一期停在 **2019-11-30**）。遇到这种，
**明说「户数数据过期，仅作参考」**，不要拿 7 年前的数据下今天筹码集中的结论。

---

## 配套：腾讯实时行情字段表

```python
raw = urllib.request.urlopen(urllib.request.Request(
    "http://qt.gtimg.cn/q=sh600698,sz002724",
    headers={"User-Agent":"Mozilla/5.0"}), timeout=20).read().decode('gbk','ignore')
f = raw.split('"')[1].split('~')
```

| 索引 | 字段 | 索引 | 字段 |
|---|---|---|---|
| `f[1]` | 名称 | `f[33]` | 最高 |
| `f[2]` | 代码 | `f[34]` | 最低 |
| `f[3]` | 现价 | `f[37]` | 成交额（万元） |
| `f[4]` | 昨收 | `f[38]` | 换手率 % |
| `f[5]` | 开盘 | `f[39]` | PE |
| `f[7]` | 内盘 | `f[44]` | **流通市值（亿）** |
| `f[8]` | 外盘 | `f[45]` | 总市值（亿） |
| `f[9]~f[18]` | 买1-5 价/量（隔位） | `f[46]` | PB |
| `f[19]~f[28]` | 卖1-5 价/量（隔位） | `f[49]` | **量比** |
| `f[30]` | 行情时间戳（`20261027092636`） | | |

**外盘占比**（主动买强度）= `f[8] / (f[7] + f[8])`。>50% 主动买占优，<45% 主动卖占优。

**涨停/跌停价**：主板 `昨收 × 1.1 / 0.9`；创业板/科创板（`30x` / `688`）`× 1.2 / 0.8`。

---

## 配套：分钟线（判断开板 / 拉升时点）

```python
m = json.loads(fetch("https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sh600698"))
rows = m['data']['sh600698']['data']['data']
# 每行 "HHMM 价格 累计成交量(手) 累计成交额(元)"
# 逐分钟量 = 相邻两行累计值相减
```

**用法**：找「某分钟放出 2-3 万手」的突变点 → 那才是资金进场/离场的时刻，比全天总量有用。

---

## 日/周 K 线

```python
# 日线（前复权）
f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600698,day,,,180,qfq"
# 周线
f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600698,week,,,120,qfq"
# 返回 data[code]["qfqday"] 或 ["day"]，每行 [日期, 开, 收, 高, 低, 量]
```

**注意**：盘中请求时最后一根 K 线是「今天」的未完成 K；要算「昨高昨低」必须用行情时间戳（`f[30]`）
判断是否已开盘，再决定取 `k[-1]` 还是 `k[-2]`（盘前取 `k[-2]` 会拿到前天，是常见 bug）。
