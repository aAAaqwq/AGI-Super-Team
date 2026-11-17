# A股数据源完整速查（实测 2026-08/09）

## 腾讯行情 qt.gtimg.cn（实时，GBK）
```
http://qt.gtimg.cn/q=sz002491          # 单只
http://qt.gtimg.cn/q=sh000001,sz399001 # 多只逗号
```
返回单行 `v_sz002491="..."`，按 `~` 分割为数组。索引表（实测）：
| idx | 含义 | idx | 含义 |
|-----|------|-----|------|
| 1 | 名称 | 32 | 涨跌% |
| 2 | 代码 | 33 | 最高 |
| 3 | 现价 | 34 | 最低 |
| 4 | 昨收 | 37 | 成交额(万元) |
| 5 | 今开 | 38 | 换手% |
| 6 | 成交量(手) | 39 | PE(TTM) |
| 30 | 时间戳 YYYYMMDDHHMMSS | 45 | 总市值(亿) |
| 31 | 涨跌额 | 47/48 | 涨停/跌停价 |

Python 拉取：`req = urllib.request.Request(url); resp.read().decode('gbk', errors='ignore')`
（新浪 hq.sinajs 同结构但更易被墙/限流，优先腾讯。）

## 日K 三源降级链（2026-10-30 实测，**必读**）

**⚠️ 腾讯 fqkline 自 2026-10 起返回 `HTTP 501 Not Implemented`**，不能作为唯一源。写任何 K 线相关脚本必须做降级。

**降级顺序：东财 push2his → 新浪 CN_MarketData → 腾讯 fqkline（已失效，仅留兜底）**

### 主源：东财 push2his（格式最清晰，量单位=手）
```
https://push2his.eastmoney.com/api/qt/stock/kline/get
  ?secid=0.002403&fields1=f1,f2,f3,f4,f5,f6
  &fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20500101&lmt=90
```
- `secid` 用上面「secid 规则」（深 `0.` / 沪 `1.` / 创业板指 `0.399006`）
- `klt=101` 日K、`fqt=1` 前复权、`lmt` 根数
- 响应 `data.klines[]`，每行是**逗号分隔字符串**：
  ```
  "2026-10-29,10.93,10.84,11.43,10.80,212469,233933551.00"
  日期,     开,   收,   高,   低,  量(手), 额(元)
  ```
  **⚠️ 注意是「开、收、高、低」，不是常见的「开、高、低、收」。** 实测校验：高 11.43 > 开 10.93 > 收 10.84 > 低 10.80。

### 备源：新浪 CN_MarketData（volume 单位是**股**，需 ÷100 转手）
```
https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData
  ?symbol=sz002403&scale=240&ma=no&datalen=90
```
- `scale=240` 日K、`datalen` 根数
- 返回 JSON 数组：`[{"day":"2026-09-10","open":"12.490","high":"13.590","low":"11.400","close":"11.700","volume":"62375028"}]`
- **字段是字符串**，要 `float()`；**volume 是股数**（62375028 股 = 62.4 万手）

### 兜底：腾讯 fqkline（2026-10 起 501，保留仅作兼容）
```
https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz002491,day,,,120,qfq
```
响应：`data.sz002491.qfqday` 数组，每行 `[date, open, close, high, low, volume]`。
注意 **close 是第 3 位**（open 第 2、close 第 3），与常见 OHLC 习惯不同，写指标代码时别搞反。

### 统一封装写法（双源自动降级）

```python
def kline(code, n=90):
    """code 可传 002403 / sh600698 / 600698.SH；返回 [{"d","o","c","h","l","v"}]，v 单位=手"""
    c = code.split(".")[0]
    sym = c if c.startswith(("sh", "sz")) else (("sh" if c.startswith("6") else "sz") + c)
    c6 = sym[2:]
    secid = ("1." if c6.startswith("6") else "0.") + c6

    # 主源：东财（开,收,高,低,量手）
    try:
        d = json.loads(http("https://push2his.eastmoney.com/api/qt/stock/kline/get"
              f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
              f"&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20500101&lmt={n}"))
        kl = (d.get("data") or {}).get("klines") or []
        if kl:
            return [{"d": p[0], "o": float(p[1]), "c": float(p[2]),
                     "h": float(p[3]), "l": float(p[4]), "v": float(p[5])}
                    for p in (s.split(",") for s in kl)]
    except Exception:
        pass

    # 备源：新浪（volume 股 → 手）
    try:
        d = json.loads(http("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
              f"CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={n}"))
        if d:
            return [{"d": x["day"], "o": float(x["open"]), "c": float(x["close"]),
                     "h": float(x["high"]), "l": float(x["low"]),
                     "v": float(x["volume"]) / 100} for x in d]
    except Exception:
        pass
    return None
```

**⚠️ 前缀处理坑**：写 `tc(code)` 这类补前缀函数时，必须先判断是否已带 `sh`/`sz`，否则 `sz399006` 会变成 `szsz399006`，接口静默返回空（本次实测踩过，排查了 3 轮才定位）。

## 东财新闻搜索（jsonp）
```
https://search-api-web.eastmoney.com/search/jsonp?cb=cb&param=<urlencoded JSON>
```
param JSON:
```json
{"uid":"","keyword":"通鼎互联","type":["cmsArticleWebOld"],"client":"web","clientType":"web",
 "clientVersion":"curr","param":{"cmsArticleWebOld":{"searchScope":"default","sort":"time",
 "pageIndex":1,"pageSize":10,"preTag":"","postTag":""}}}
```
剥壳：`m = re.search(r'cb\((.*)\)$', raw, re.S); d = json.loads(m.group(1))`
取 `d['result']['cmsArticleWebOld']`，每条 `date/title/content/mediaName`。
可用 keyword：个股名、板块名+"收评/涨停/主线"、宏观("美联储 加息")。这是信息面/连板数/题材热度的主要来源。

## 东财财务 F10（中英混合字段）
```
https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew?type=0&code=SZ002491
```
code 必须带交易所前缀大写：SH600183 / SZ002491。响应 `data[]` 按报告期倒序。
| 字段 | 含义 | | 字段 | 含义 |
|------|------|-|------|------|
| REPORT_DATE | 报告期 | | TOTALOPERATEREVETZ | 营收同比% |
| TOTALOPERATEREVE | 营业总收入(元) | | PARENTNETPROFITTZ | 净利同比% |
| PARENTNETPROFIT | 归母净利(元) | | KCFJCXSYJLRTZ | 扣非同比% |
| KCFJCXSYJLR | 扣非净利(元) | | XSMLL | 毛利率% |
| ROEJQ | 加权ROE% | | EPSJB | 基本EPS |
| MGJYXJJE | 每股经营现金流 | | BPS | 每股净资产 |

## 东财题材归属 F10 CoreConception
```
https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax?code=SZ002235
```
响应 dict：`gnbk`(概念板块) / `hybk`(行业板块) / `ssbk`(省份板块) / `fgnbk`，每项含 `BOARD_NAME`。
所有板块平铺拼接即"东财概念标签"。筛选"核心题材"= 取与当日热点新闻吻合的标签。

## 东财龙虎榜（数据中心）
```
https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD_DETAILSNEW
  &columns=ALL&filter=(TRADE_DATE='2026-09-02')(SECURITY_CODE="002104")&pageNumber=1&pageSize=20
  &sortTypes=-1&sortColumns=BILLBOARD_NET_AMT
```
字段：BILLBOARD_NET_AMT(净额，负=净卖)、BILLBOARD_BUY_AMT/SELL_AMT、BUY_SEAT/SELL_SEAT、TURNOVERRATE、
CHANGE_RATE、CLOSE_PRICE、EXPLAIN(上榜原因)、DEAL_AMOUNT_RATIO、SUM_BUY_AMT/SUM_SELL_AMT。
- 席位明细：reportName=RPT_BILLBOARD_TRADEDETAIL（不稳定，可能 null → 用新闻兜底）
- 无记录时 result.data 为空数组 → 说明当日未上榜。
- 换手榜原因= "日换手率达到20%的前5只"；异动原因= 涨幅偏离。

## 东财资金流
历史日线：
```
https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=0&klt=101&secid=0.002104
  &fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56
```
klines 每行：`date,主力净额,小单,中单,大单,超大单`（单位元）。字段对应 f52=主力 f53=小单 f54=中单 f55=大单 f56=超大单。
⚠️ 该接口高频请求报 `Remote end closed connection without response` 或 429 → 每股间隔 3-5s 重试，仍失败换新浪。

新浪资金流（更稳，日级多日）：
```
https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_qsfx_zjlrqs?page=1&num=5&sort=opendate&asc=0&daima=sz002104
```
返回 JSON 数组：`opendate/trade/changeratio/turnover/netamount(净流入)/ratioamount(净占比)/r0_net(超大单)/r0_ratio`。

## 东财公告
```
https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=10&page_index=1&ann_type=A&client_source=web&stock_list=002491
```
`data.list[]`：notice_date/title/columns[0].column_name(类型)。类型含：股票交易异常波动/半年报全文/董事会决议/质押/减持/分红/业绩预告等。

## secid 规则
东财 push2/datacenter 用 secid：深市 `0.002104`、沪市 `1.600183`、上证指数 `1.000001`、深成 `0.399001`、创业板 `0.399006`。

## 常用指数/板块名称
- 上证 sh000001、深成 sz399001、创业板 sz399006
- 沪深300 sh000300、科创50 sh000688

## 备注
- 所有东财接口建议带 `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)` + `Referer`（data.eastmoney.com / quote.eastmoney.com / emweb.securities.eastmoney.com 视接口而定）。
- 腾讯接口 Referer http://gu.qq.com/ 一般可省。
