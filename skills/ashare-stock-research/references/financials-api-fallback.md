# A股财务数据接口：可用与不可用（2026-10-27 实测）

用户问「全面分析基本面」时的取数路径。**东财 F10 老接口已不可用，用 datacenter 的业绩报表接口替代。**

## ✅ 可用：东财 datacenter 业绩报表（首选）

```python
import urllib.request, json, urllib.parse

u = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD"
     "&columns=ALL&filter=" + urllib.parse.quote('(SECURITY_CODE="600698")') +
     "&pageNumber=1&pageSize=6&sortTypes=-1&sortColumns=REPORTDATE&source=WEB&client=WEB")
raw = urllib.request.urlopen(urllib.request.Request(
    u, headers={"User-Agent":"Mozilla/5.0","Referer":"https://data.eastmoney.com/"}), timeout=25
).read().decode('utf-8','ignore')

rows = json.loads(raw)["result"]["data"]
```

### 字段映射（关键，名字和直觉不一样）

| 想要 | 字段 | 单位处理 |
|---|---|---|
| 报告期 | `REPORTDATE` | |
| 营业收入 | `TOTAL_OPERATE_INCOME` | **÷1e8 → 亿** |
| 营收同比 | `YSTZ` | 已是 % |
| 归母净利润 | `PARENT_NETPROFIT` | **÷1e8 → 亿** |
| 净利同比 | `SJLTZ` | 已是 % |
| 毛利率 | `XSMLL` | 已是 % |
| 加权 ROE | `WEIGHTAVG_ROE` | 已是 % |

**实测输出（湖南天雁 600698，2026-10-27）**：

| 报告期 | 营收(亿) | 营收同比 | 净利(亿) | 净利同比 | 毛利率 | ROE |
|---|---|---|---|---|---|---|
| 2026-06-30 | 3.073 | +29.56% | 0.021 | +75.40% | 10.28% | 0.27% |
| 2026-03-31 | 1.621 | +46.41% | 0.018 | +109.54% | 11.23% | 0.25% |
| 2025-12-31 | 5.160 | +19.30% | **−0.313** | −860.50% | 8.88% | −4.16% |

## ❌ 不可用 / 别再试的

| 接口 | 现象 |
|---|---|
| `emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/MainTargetAjax?type=0&code=SH600698` | 返回空串或带 BOM 的 HTML；`utf-8-sig` 解码后仍是 `Expecting value: line 1 column 1` |
| `datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_FINANCE_MAINFINADATA` | 返回 6 条但**所有字段名为空**（每列都打成 `-`），字段名与预期不符 |
| `web.ifzq.gtimg.cn/appstock/app/StockData/stockFinancial?param=sh600698,1,5` | `Can't load controller:StockDataController` |
| `money.finance.sina.com.cn/corp/go.php/vFD_FinanceSummary/stockid/600698.phtml` | GBK 页面可下载但表格解析为空 |

## 基本面快速判读（配合游资框架用）

拿到财报后，**只回答两个问题**：

1. **利润是真的吗**：营收增长但净利极薄（如 2026H1 营收 3.07 亿、净利 210 万、毛利率 10.28%、
   ROE 0.27%）→ 低端制造，无定价权，**股价与基本面无关，是纯题材/资金票**。
2. **贵不贵**：PB 是最直观的（湖南天雁 PB 10.82 = 一块钱净资产卖 10.8 块）。
   PE 为负时不要写「PE −263 倍」，写「微利导致 PE 失真，实际净利 210 万」。

**结论话术**：「基本面不支持长拿，只能做短线，赚了就走」——
用户是短线交易者，说清「不能因为亏损就变成长期持有」比罗列财务比率有用。
