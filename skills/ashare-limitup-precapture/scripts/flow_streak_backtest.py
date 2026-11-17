#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金连续性回测（验证「连续流入 > 单日流入」）

用法:
  python3 flow_streak_backtest.py                 # 默认 100 只活跃股
  python3 flow_streak_backtest.py --pool 200      # 200 只
  python3 flow_streak_backtest.py --days 130      # 回溯天数

输出:
  各信号（单日/连续2日/连续3日/连续4日+）的 T+1/T+3/T+5 收益与胜率
  以及「连续3日 + 涨停 + 累计金额」的组合分层

2026-11-17 实测结果（98 只 / 11,127 样本）:
  单日流入        T+3 -0.11%  胜率46%
  连续3日         T+3 +1.14%  胜率50%
  连续3日+涨停+累计<5亿  T+5 +11.32% 胜率71%  ← 最优
  单日流入+涨停          T+5 +2.82%  胜率53%
"""
import urllib.request
import json
import time
import random
import argparse
import statistics

H = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}


def fetch(url, t=20, tries=2):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=t).read().decode("utf-8", "ignore")
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.5)


def build_pool(size):
    """按成交额取活跃股，剔除 ST"""
    pool = []
    pages = (size // 100) + 1
    for pn in range(1, pages + 1):
        r = fetch(f"https://push2.eastmoney.com/api/qt/clist/get?pn={pn}&pz=100&po=1&np=1&fltt=2&invt=2&fid=f6"
                  f"&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f13,f14")
        if not r:
            continue
        for x in (json.loads(r).get("data") or {}).get("diff") or []:
            nm = x.get("f14") or ""
            if any(s in nm for s in ("ST", "退")):
                continue
            pool.append((("1." if x.get("f13") == 1 else "0.") + x["f12"], x["f12"], nm))
        time.sleep(0.2)
    return pool[:size]


def load_flow(secid, days):
    """返回 [{d, sup, c}]；sup 单位亿"""
    u = (f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt={days}&klt=101&secid={secid}"
         f"&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f62,f63")
    r = fetch(u, t=12)
    if not r:
        return None
    try:
        kl = (json.loads(r).get("data") or {}).get("klines") or []
    except Exception:
        return None
    out = []
    for line in kl:
        p = line.split(",")
        if len(p) < 7:
            continue
        try:
            out.append({"d": p[0], "sup": float(p[5]) / 1e8, "c": float(p[6]) if p[6] else 0})
        except Exception:
            continue
    return out if len(out) >= 60 else None


def stat(name, recs):
    if len(recs) < 10:
        print(f"{name:<42}样本{len(recs):>4} 太少")
        return
    f1 = [x["f1"] for x in recs if x["f1"] is not None]
    f3 = [x["f3"] for x in recs if x["f3"] is not None]
    f5 = [x["f5"] for x in recs if x["f5"] is not None]
    def w(v):
        return sum(1 for x in v if x > 0) / len(v) * 100 if v else 0
    print(f"{name:<42}{len(recs):>5}"
          f"{statistics.mean(f1) if f1 else 0:>+8.2f}%{w(f1):>6.0f}%"
          f"{statistics.mean(f3) if f3 else 0:>+8.2f}%{w(f3):>6.0f}%"
          f"{statistics.mean(f5) if f5 else 0:>+8.2f}%{w(f5):>6.0f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=int, default=100)
    ap.add_argument("--days", type=int, default=130)
    args = ap.parse_args()

    print(f"⏰ 资金连续性回测 | 池 {args.pool} 只 | 回溯 {args.days} 日\n")
    pool = build_pool(args.pool)
    print(f"股票池 {len(pool)} 只，开始拉资金流...")

    data = []
    for secid, code, nm in pool:
        rows = load_flow(secid, args.days)
        if rows:
            data.append({"code": code, "nm": nm, "rows": rows})
        time.sleep(0.12)
    print(f"成功 {len(data)} 只\n")

    sig = {"连续4日+": [], "连续3日": [], "连续2日": [], "单日": []}
    allrec = []
    streak3 = []

    for info in data:
        rows = info["rows"]
        closes = [r["c"] for r in rows]
        n = len(rows)
        for i in range(3, n - 5):
            c = rows[i]["c"]
            if c <= 0 or closes[i - 1] <= 0:
                continue
            s = [rows[i - k]["sup"] for k in range(0, 6)]
            f1 = (rows[i + 1]["c"] / c - 1) * 100
            f3 = (rows[i + 3]["c"] / c - 1) * 100
            f5 = (rows[i + 5]["c"] / c - 1) * 100
            chg = (c / closes[i - 1] - 1) * 100
            allrec.append({"f1": f1, "f3": f3, "f5": f5})

            if s[0] < 0:
                continue
            rec = {"f1": f1, "f3": f3, "f5": f5, "chg": chg,
                   "cum3": s[0] + s[1] + s[2], "cum5": sum(s[:5])}
            if s[0] > 0 and s[1] > 0 and s[2] > 0:
                sig["连续3日"].append(rec)
                streak3.append(rec)
                if s[3] > 0:
                    sig["连续4日+"].append(rec)
            elif s[0] > 0 and s[1] > 0 and s[2] <= 0:
                sig["连续2日"].append(rec)
            elif s[0] > 0 and s[1] < 0:
                sig["单日"].append(rec)

    print(f"{'信号':<42}{'样本':>5}{'T+1':>8}{'胜':>6}{'T+3':>8}{'胜':>6}{'T+5':>8}{'胜':>6}")
    print("-" * 92)
    stat("【基准】全交易日", allrec)
    for k in ["单日", "连续2日", "连续3日", "连续4日+"]:
        stat(k, sig[k])

    print(f"\n{'组合信号（连续3日内部）':<42}{'样本':>5}{'T+1':>8}{'胜':>6}{'T+3':>8}{'胜':>6}{'T+5':>8}{'胜':>6}")
    print("-" * 92)
    stat("连续3日 + 当日涨停(>9.5%) + 累计<5亿",
         [x for x in streak3 if x["chg"] > 9.5 and x["cum3"] < 5])
    stat("连续3日 + 当日涨停(>9.5%)",
         [x for x in streak3 if x["chg"] > 9.5])
    stat("连续3日 + 当日>6% + 累计<5亿",
         [x for x in streak3 if x["chg"] > 6 and x["cum3"] < 5])
    stat("连续3日 + 当日跌 + 累计0.5~5亿",
         [x for x in streak3 if x["chg"] < -1 and 0.5 <= x["cum3"] < 5])

    print(f"\n【按 3 日累计超大单分层】")
    for lo, hi, label in [(0, 0.5, "<0.5亿"), (0.5, 2, "0.5~2亿"),
                          (2, 5, "2~5亿"), (5, 1e9, ">5亿")]:
        stat(label, [x for x in streak3 if lo <= x["cum3"] < hi])

    print("\n⚠️ 结果为历史统计，不代表未来。仅供方法参考。")


if __name__ == "__main__":
    main()
