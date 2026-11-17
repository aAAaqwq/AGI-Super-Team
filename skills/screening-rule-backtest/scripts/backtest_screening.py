#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股规则回测验证 —— 三项必做检验一键跑

用法:
  # 1. 拉股票池 + 历史K线（缓存到 /tmp/btr/）
  python3 backtest_screening.py fetch --ltsz 30 200 --sample 800 --days 500

  # 2. 跑内置策略 + 基准（自动做三项检验）
  python3 backtest_screening.py run

  # 3. 测自定义条件（Python 表达式，变量见下）
  python3 backtest_screening.py test --cond "gap>2 and dist30<-15"

条件可用变量（每行 = 一个股票一个交易日）:
  chg      当日涨跌幅 %
  vr       量 / 20日均量
  vr5      量 / 5日均量
  to       换手率 %
  dist30   距 MA30 的偏离 %
  drop5    近5日涨幅 %
  gap      今日开盘 / 昨收 - 1 的 %
  up5      近5日阳线数
  dist_low20   距20日低点 %
  dist_high20  距20日高点 %
  zt20     近20日涨停次数
  max_lb   近60日最大连板

收益变量: r1 / r3 / r5（次日开盘买入，T+1/T+3/T+5 收盘卖出）
"""
import argparse
import json
import os
import random
import statistics
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

H = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
CACHE_DIR = "/tmp/btr"
BJ = timezone(timedelta(hours=8))


def http(url, enc="utf-8", timeout=15, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=H)
            return urllib.request.urlopen(req, timeout=timeout).read().decode(enc, "ignore")
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.5)


def is_gem(code):
    return code.startswith(("300", "301", "688", "689"))


def limit_pct(code):
    return 19.5 if is_gem(code) else 9.5


# ---------------------------------------------------------------- fetch

def cmd_fetch(args):
    os.makedirs(CACHE_DIR, exist_ok=True)
    pool_file = f"{CACHE_DIR}/pool.json"

    if not os.path.exists(pool_file):
        print(f"拉全市场股票池（流通 {args.ltsz[0]}-{args.ltsz[1]} 亿）...")
        allst = []
        for page in range(1, 60):
            r = http(f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                     f"Market_Center.getHQNodeData?page={page}&num=100&sort=symbol&asc=1&node=hs_a",
                     tries=2)
            if not r:
                break
            try:
                d = json.loads(r)
            except Exception:
                break
            if not d:
                break
            for x in d:
                try:
                    sym = str(x.get("symbol") or "")
                    nm = str(x.get("name") or "")
                    if not sym or "ST" in nm or "退" in nm:
                        continue
                    px = float(x.get("trade") or 0)
                    nmc = float(x.get("nmc") or 0) / 1e4   # 万元 → 亿
                    if px <= 0 or nmc <= 0:
                        continue
                    if args.ltsz[0] <= nmc <= args.ltsz[1]:
                        allst.append({"sym": sym, "code": sym[2:], "name": nm, "ltsz": round(nmc, 2)})
                except Exception:
                    pass
            time.sleep(0.12)
        json.dump(allst, open(pool_file, "w"), ensure_ascii=False)
        print(f"  池子 {len(allst)} 只 → {pool_file}")

    pool = json.load(open(pool_file))
    random.seed(42)
    sample = random.sample(pool, min(args.sample, len(pool)))
    print(f"抽样 {len(sample)} 只，拉 {args.days} 日 K 线...")

    data = {}
    t0 = time.time()
    for i, x in enumerate(sample):
        sym = x["sym"]
        r = http(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                 f"CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={args.days}", tries=2)
        if r:
            try:
                d = json.loads(r)
                if d and len(d) >= 60:
                    data[sym] = {
                        "name": x["name"], "ltsz": x["ltsz"],
                        "k": [{"d": y["day"], "o": float(y["open"]), "c": float(y["close"]),
                               "h": float(y["high"]), "l": float(y["low"]),
                               "v": float(y["volume"]) / 100} for y in d],
                    }
            except Exception:
                pass
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(sample)} ok={len(data)} {time.time()-t0:.0f}s")
        time.sleep(0.05)

    out = f"{CACHE_DIR}/data.json"
    json.dump(data, open(out, "w"), ensure_ascii=False)
    ds = sorted({y["d"] for v in data.values() for y in v["k"]})
    print(f"\n✅ {len(data)} 只 → {out}")
    print(f"   交易日 {len(ds)} 天: {ds[0]} ~ {ds[-1]}")


# ---------------------------------------------------------------- build rows

def build_rows():
    path = f"{CACHE_DIR}/data.json"
    if not os.path.exists(path):
        sys.exit("先跑 fetch")
    data = json.load(open(path))

    rows = []
    for sym, v in data.items():
        k = v["k"]
        if len(k) < 60:
            continue
        fs = v["ltsz"] * 1e8 / k[-1]["c"] if k[-1]["c"] > 0 else 0
        if fs <= 0:
            continue
        lp = limit_pct(sym[2:])
        c = [x["c"] for x in k]
        o = [x["o"] for x in k]
        h = [x["h"] for x in k]
        l = [x["l"] for x in k]
        vol = [x["v"] for x in k]
        n = len(k)

        for i in range(35, n - 1):
            v20 = sum(vol[i - 20:i]) / 20
            v5 = sum(vol[i - 5:i]) / 5
            if v20 <= 0 or v5 <= 0:
                continue
            ma30 = sum(c[i - 29:i + 1]) / 30
            buy = o[i + 1]
            if buy <= 0:
                continue

            zt_flags = [(c[j] / c[j - 1] - 1) * 100 >= lp for j in range(max(1, i - 59), i + 1)]
            mx = cur = 0
            for f in zt_flags:
                cur = cur + 1 if f else 0
                mx = max(mx, cur)

            low20 = min(l[i - 19:i + 1])
            high20 = max(h[i - 19:i + 1])

            rows.append({
                "sym": sym, "nm": v["name"], "d": k[i]["d"],
                "yr": k[i]["d"][:4], "m": k[i]["d"][:7],
                "chg": (c[i] / c[i - 1] - 1) * 100,
                "vr": vol[i] / v20, "vr5": vol[i] / v5,
                "to": vol[i] * 100 / fs * 100,
                "dist30": (c[i] / ma30 - 1) * 100,
                "drop5": (c[i] / c[i - 5] - 1) * 100,
                "gap": (o[i] / c[i - 1] - 1) * 100,
                "up5": sum(1 for j in range(i - 4, i + 1) if c[j] > c[j - 1]),
                "dist_low20": (c[i] / low20 - 1) * 100,
                "dist_high20": (c[i] / high20 - 1) * 100,
                "zt20": sum(1 for j in range(max(1, i - 19), i + 1)
                            if (c[j] / c[j - 1] - 1) * 100 >= lp),
                "max_lb": mx,
                "r1": (c[i + 1] / buy - 1) * 100,
                "r3": (c[i + 3] / buy - 1) * 100 if i + 3 < n else None,
                "r5": (c[i + 5] / buy - 1) * 100 if i + 5 < n else None,
            })
    return rows


# ---------------------------------------------------------------- stats

def stat(lst, key):
    v = [x[key] for x in lst if x.get(key) is not None]
    if not v:
        return (0.0, 0.0, 0)
    return (sum(1 for x in v if x > 0) / len(v) * 100, statistics.mean(v), len(v))


def three_checks(rows, cond, label):
    """三项必做检验 + 分年/分月超额"""
    all_sub = [r for r in rows if cond(r)]
    if len(all_sub) < 50:
        print(f"\n【{label}】信号只有 {len(all_sub)} 个，样本不足，不下结论。")
        return

    print(f"\n{'='*78}")
    print(f"【{label}】{len(all_sub)} 个信号")
    print("="*78)

    # --- 检验② 集中度
    dc = Counter(r["d"] for r in all_sub)
    top5 = sum(n for _, n in dc.most_common(5))
    print(f"\n检验② 信号集中度：{len(dc)} 个交易日，前5日占 {top5/len(all_sub)*100:.1f}%")
    print(f"  最多的5天: {dc.most_common(5)}")
    verdict = "✅ 均匀" if top5 / len(all_sub) <= 0.20 else "🔴 过度集中（结论不可信）"
    print(f"  → {verdict}")

    excl = {d for d, _ in dc.most_common(5)}
    clean = [r for r in all_sub if r["d"] not in excl]
    print(f"\n  剔除前5日后: {len(clean)} 个信号")
    for key, lb in (("r1", "T+1"), ("r3", "T+3"), ("r5", "T+5")):
        w, a, c = stat(all_sub, key)
        w2, a2, c2 = stat(clean, key)
        print(f"    {lb}: 全部 {w:.1f}% / {a:+.2f}%  →  剔除后 {w2:.1f}% / {a2:+.2f}%")

    # --- 检验③ 分年分月超额
    base_by_m = defaultdict(list)
    base_by_y = defaultdict(list)
    for r in rows:
        base_by_m[r["m"]].append(r)
        base_by_y[r["yr"]].append(r)

    sub_by_m = defaultdict(list)
    sub_by_y = defaultdict(list)
    for r in all_sub:
        sub_by_m[r["m"]].append(r)
        sub_by_y[r["yr"]].append(r)

    print(f"\n检验③ 分年超额（策略 − 同年基准）：")
    pos_y = tot_y = 0
    for y in sorted(sub_by_y):
        s = sub_by_y[y]
        if len(s) < 50:
            continue
        _, a1, _ = stat(s, "r1")
        _, b1, _ = stat(base_by_y[y], "r1")
        e = a1 - b1
        tot_y += 1
        pos_y += 1 if e > 0 else 0
        print(f"  {y}: 策略 {a1:+.2f}%  基准 {b1:+.2f}%  超额 {e:+.2f}%  {'✅' if e > 0.15 else ('❌' if e < -0.15 else '➖')}")

    print(f"\n  分月超额：")
    pos_m = tot_m = 0
    for m in sorted(sub_by_m):
        s = sub_by_m[m]
        if len(s) < 30:
            continue
        _, a1, _ = stat(s, "r1")
        _, b1, _ = stat(base_by_m[m], "r1")
        e = a1 - b1
        tot_m += 1
        pos_m += 1 if e > 0 else 0
        print(f"    {m}: 超额 {e:+.2f}%  {'✅' if e > 0.15 else ('❌' if e < -0.15 else '➖')}")

    if tot_m:
        print(f"\n  → 正超额月份 {pos_m}/{tot_m} = {pos_m/tot_m*100:.0f}%"
              f"（≥60% 才算稳）{'✅' if pos_m/tot_m >= 0.6 else '🔴'}")

    # --- 三周期
    print(f"\n三周期：")
    for key, lb in (("r1", "T+1"), ("r3", "T+3"), ("r5", "T+5")):
        w, a, c = stat(all_sub, key)
        wb, ab, _ = stat(rows, key)
        print(f"  {lb}: 策略 {w:.1f}% / {a:+.2f}%   基准 {wb:.1f}% / {ab:+.2f}%   超额 {a-ab:+.2f}%")


# ---------------------------------------------------------------- commands

BUILTIN = {
    "基准（全样本）": lambda r: True,
    "高开>2%": lambda r: r["gap"] > 2,
    "量≥2倍": lambda r: r["vr"] >= 2,
    "距MA30>+30%（高位）": lambda r: r["dist30"] > 30,
    "距MA30<-25%（深跌）": lambda r: r["dist30"] < -25,
    "超跌反弹（低位+跌>10%）": lambda r: r["dist30"] < -15 and r["drop5"] < -10,
    "多头排列近似（近5日阳线≥4）": lambda r: r["up5"] >= 4,
    "涨停基因（20日涨停≥2）": lambda r: r["zt20"] >= 2,
    "涨停基因+户数型小盘（20日涨停≥2且流通<50亿）": lambda r: r["zt20"] >= 2 and r["dist30"] > -20,
}


def cmd_run(args):
    rows = build_rows()
    print(f"总样本 {len(rows):,} 个（{len({r['sym'] for r in rows})} 只股票，"
          f"{len({r['d'] for r in rows})} 个交易日）")
    w, a, _ = stat(rows, "r1")
    w5, a5, _ = stat(rows, "r5")
    print(f"基准: T+1 {w:.1f}% / {a:+.2f}%   T+5 {w5:.1f}% / {a5:+.2f}%")

    for name, cond in BUILTIN.items():
        if name.startswith("基准"):
            continue
        three_checks(rows, cond, name)


def cmd_test(args):
    rows = build_rows()
    print(f"总样本 {len(rows):,}")
    cond = eval(f"lambda r: {args.cond}")   # noqa: S307 — 本地脚本，输入来自用户自己
    three_checks(rows, cond, args.cond)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("--ltsz", nargs=2, type=float, default=[30, 200])
    f.add_argument("--sample", type=int, default=800)
    f.add_argument("--days", type=int, default=500)
    f.set_defaults(func=cmd_fetch)

    r = sub.add_parser("run")
    r.set_defaults(func=cmd_run)

    t = sub.add_parser("test")
    t.add_argument("--cond", required=True)
    t.set_defaults(func=cmd_test)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
