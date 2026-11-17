#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股一键流水线：报价 + 技术指标 + K线 + 新闻 + 财务摘要
用法:
  python3 a_share_pipeline.py 002491                    # 深市默认；6开头自动判沪市
  python3 a_share_pipeline.py 600522 --days 60
  python3 a_share_pipeline.py 002491 --news --peers sz600498,sh600522,sh601869
数据源：腾讯行情（实时+K线，GBK）+ 东方财富（新闻/财务）。纯标准库，无需 pip。
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://finance.sina.com.cn"}

def http_get(url, encoding="utf-8"):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode(encoding, errors="ignore")

def tencent_symbol(code):
    return ("sh" if code.startswith("6") else "sz") + code

def quote(code):
    """腾讯实时报价 → dict；字段按 ~ 分割（GBK）"""
    raw = http_get(f"http://qt.gtimg.cn/q={tencent_symbol(code)}", "gbk")
    p = raw.split("~")
    if len(p) < 35:
        return None
    return {
        "name": p[1], "code": p[2], "price": float(p[3]), "prev_close": float(p[4]),
        "open": float(p[5]), "pct": float(p[32]), "high": float(p[33]),
        "low": float(p[34]), "volume_hand": int(p[6]),
    }

def kline(code, days=120):
    """腾讯前复权日K → [[date, open, close, high, low, volume], ...]（顺序: 开/收/高/低）"""
    sym = tencent_symbol(code)
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={sym},day,,,{days},qfq"
    d = json.loads(http_get(url))["data"][sym]
    key = "qfqday" if "qfqday" in d else "day"
    return d[key]

def ma(data, n):
    out, s = [], 0
    for i, v in enumerate(data):
        s += v
        if i >= n:
            s -= data[i - n]
        out.append(s / min(n, i + 1))
    return out

def rsi(data, n=14):
    out = [None] * len(data)
    if len(data) <= n:
        return out
    gains = losses = 0
    for i in range(1, n + 1):
        ch = data[i] - data[i - 1]
        gains += max(ch, 0); losses += max(-ch, 0)
    avg_g, avg_l = gains / n, losses / n
    out[n] = 100 - 100 / (1 + (avg_g / avg_l if avg_l else 999))
    for i in range(n + 1, len(data)):
        ch = data[i] - data[i - 1]
        avg_g = (avg_g * (n - 1) + max(ch, 0)) / n
        avg_l = (avg_l * (n - 1) + max(-ch, 0)) / n
        out[i] = 100 - 100 / (1 + (avg_g / avg_l if avg_l else 999))
    return out

def macd(data, fast=12, slow=26, signal=9):
    def ema(d, n):
        out, m = [d[0]], 2 / (n + 1)
        for v in d[1:]:
            out.append(v * m + out[-1] * (1 - m))
        return out
    ef, es = ema(data, fast), ema(data, slow)
    dif = [a - b for a, b in zip(ef, es)]
    dea = ema(dif, signal)
    return dif, dea, [(a - b) * 2 for a, b in zip(dif, dea)]

def news(keyword, n=8):
    """东财新闻搜索（JSONP 剥壳）"""
    param = {
        "uid": "", "keyword": keyword, "type": ["cmsArticleWebOld"],
        "client": "web", "clientType": "web", "clientVersion": "curr",
        "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "time",
                  "pageIndex": 1, "pageSize": n, "preTag": "", "postTag": ""}},
    }
    url = "https://search-api-web.eastmoney.com/search/jsonp?cb=cb&param=" + urllib.parse.quote(json.dumps(param, ensure_ascii=False))
    raw = http_get(url)
    m = re.search(r"cb\((.*)\)\s*$", raw, re.S)
    d = json.loads(m.group(1))
    arts = (d.get("result") or {}).get("cmsArticleWebOld") or []
    return [{"date": a.get("date", "")[:16], "title": a.get("title", ""),
             "media": a.get("mediaName", "")} for a in arts]

def finance(code):
    """东财 F10 财务摘要（最新一期）"""
    sc = "SZ" + code if code.startswith("0") or code.startswith("3") else "SH" + code
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew?type=0&code={sc}"
    try:
        d = json.loads(http_get(url))
        r = d["data"][0]
        return {
            "date": r.get("REPORT_DATE", "")[:10],
            "revenue_yi": round((r.get("TOTALOPERATEREVE") or 0) / 1e8, 2),
            "rev_yoy": round(r.get("TOTALOPERATEREVETZ") or 0, 1),
            "profit_yi": round((r.get("PARENTNETPROFIT") or 0) / 1e8, 3),
            "profit_yoy": round(r.get("PARENTNETPROFITTZ") or 0, 1),
            "kcjl_yoy": round(r.get("KCFJCXSYJLRTZ") or 0, 1),
            "gross_margin": round(r.get("XSMLL") or 0, 1),
            "roe": round(r.get("ROEJQ") or 0, 2),
            "eps": r.get("EPSJB"),
        }
    except Exception as e:
        return {"error": str(e)}

def fmt(n):
    if n >= 1e8: return f"{n/1e8:.2f}亿"
    if n >= 1e4: return f"{n/1e4:.1f}万"
    return str(n)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("code", help="6位股票代码，如 002491 / 600522")
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--news", action="store_true", help="抓新闻")
    ap.add_argument("--peers", help="板块对比代码，逗号分隔（带前缀），如 sz600498,sh601869")
    args = ap.parse_args()

    q = quote(args.code)
    if not q:
        print("报价获取失败"); return
    print(f"=== {q['name']}({q['code']}) 现价 {q['price']} ({q['pct']:+.2f}%) ===")
    print(f"今开 {q['open']} 高 {q['high']} 低 {q['low']} 昨收 {q['prev_close']} 量 {fmt(q['volume_hand'])}手")

    if args.peers:
        print("\n【板块对比】")
        for c in args.peers.split(","):
            pq = quote(c)
            if pq:
                print(f"  {pq['name']}: {pq['price']} ({pq['pct']:+.2f}%)")

    k = kline(args.code, args.days)
    closes = [float(r[2]) for r in k]
    i = len(closes) - 1
    ma5, ma10, ma20, ma60 = ma(closes, 5), ma(closes, 10), ma(closes, 20), ma(closes, 60)
    r = rsi(closes)
    dif, dea, hist = macd(closes)
    print("\n【技术指标】")
    print(f"  MA5 {ma5[i]:.2f} MA10 {ma10[i]:.2f} MA20 {ma20[i]:.2f} MA60 {ma60[i]:.2f}")
    print(f"  RSI14 {r[i]:.1f} | MACD DIF {dif[i]:.3f} DEA {dea[i]:.3f} HIST {hist[i]:.3f}")
    print(f"  近5日 {(closes[i]/closes[i-5]-1)*100:+.1f}% 近10日 {(closes[i]/closes[i-10]-1)*100:+.1f}% 近{min(30,i)}日 {(closes[i]/closes[max(0,i-30)]-1)*100:+.1f}%")
    print(f"  多头排列 {ma5[i]>ma10[i]>ma20[i]} 收盘>MA5 {closes[i]>ma5[i]} MA20>MA60 {ma20[i]>ma60[i]}")

    if args.news:
        print("\n【最近新闻】")
        for a in news(q["name"], 8):
            print(f"  {a['date']} | {a['title']} ({a['media']})")

    fin = finance(args.code)
    if fin and "error" not in fin:
        print("\n【财务摘要】")
        print(f"  {fin['date']}: 营收 {fin['revenue_yi']}亿({fin['rev_yoy']:+.1f}%) 净利 {fin['profit_yi']}亿({fin['profit_yoy']:+.1f}%) 扣非同比 {fin['kcjl_yoy']:+.1f}%")
        print(f"  毛利率 {fin['gross_margin']}% ROE {fin['roe']}% EPS {fin['eps']}")

if __name__ == "__main__":
    main()
