#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大盘大跌后反弹概率回测（盘前预判用）

用途：用户问「今天会反弹吗」时，不要靠盘感 —— 拉指数历史，
      按「今天的特征」抽同构样本，给出次日/3日/5日的基准率。

用法：
  # 创业板，单日跌超 4%
  python3 rebound_probability.py --symbol sz399006 --threshold -4

  # 深成指，单日跌超 3%，且要求前置连跌 >=3 天
  python3 rebound_probability.py --symbol sz399001 --threshold -3 --min-streak 3

  # 同时交叉验证两个指数
  python3 rebound_probability.py --symbol sz399006 --threshold -4 --cross sz399001:3

  # 拉更长历史
  python3 rebound_probability.py --symbol sz399006 --threshold -4 --days 1200
"""
import urllib.request
import json
import argparse
import statistics
import time

H = {"User-Agent": "Mozilla/5.0"}


def fetch(url, t=25, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=t).read().decode("utf-8", "ignore")
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(1.0)


def load_klines(symbol, days):
    url = (f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
           f"?symbol={symbol}&scale=240&ma=no&datalen={days}")
    r = fetch(url)
    if not r:
        return []
    try:
        return [{"d": x["day"], "o": float(x["open"]), "h": float(x["high"]),
                 "l": float(x["low"]), "c": float(x["close"])} for x in json.loads(r)]
    except Exception:
        return []


def analyse(klines, threshold, min_streak=0, label=""):
    """返回样本列表 + 统计"""
    c = [x["c"] for x in klines]
    n = len(c)
    samples = []
    for i in range(1, n):
        chg = (c[i] / c[i - 1] - 1) * 100
        if chg > threshold:
            continue
        # 前置连跌天数
        streak = 0
        j = i
        while j > 0 and c[j] < c[j - 1]:
            streak += 1
            j -= 1
        if streak < min_streak:
            continue
        nxt = (c[i + 1] / c[i] - 1) * 100 if i + 1 < n else None
        d3 = (c[i + 3] / c[i] - 1) * 100 if i + 3 < n else None
        d5 = (c[i + 5] / c[i] - 1) * 100 if i + 5 < n else None
        samples.append({"date": klines[i]["d"], "chg": chg, "streak": streak,
                        "nxt": nxt, "d3": d3, "d5": d5})

    print(f"\n{'='*72}")
    print(f"{label or ''} 条件：单日跌 <= {threshold}%" + (f" 且前置连跌 >= {min_streak} 天" if min_streak else ""))
    print(f"数据区间：{klines[0]['d']} ~ {klines[-1]['d']}（{len(klines)} 根）")
    print(f"命中样本：{len(samples)} 次")
    print(f"{'='*72}")

    if not samples:
        print("  ⚠️ 样本为 0，放宽阈值再试")
        return samples

    print(f"\n{'日期':<12}{'跌幅':>8}{'前置连跌':>9}{'次日':>9}{'3日后':>9}{'5日后':>9}")
    for s in samples:
        f = lambda v: f"{v:+.2f}%" if v is not None else "—"
        print(f"{s['date']:<12}{s['chg']:>8.2f}{s['streak']:>9}{f(s['nxt']):>9}{f(s['d3']):>9}{f(s['d5']):>9}")

    for key, name in [("nxt", "次日"), ("d3", "3日后"), ("d5", "5日后")]:
        vals = [s[key] for s in samples if s[key] is not None]
        if not vals:
            continue
        up = sum(1 for v in vals if v > 0)
        print(f"\n{name}：样本 {len(vals)} | 上涨 {up}（{up/len(vals)*100:.0f}%）"
              f" | 均值 {statistics.mean(vals):+.2f}% | 中位 {statistics.median(vals):+.2f}%"
              f" | 最好 {max(vals):+.2f}% | 最差 {min(vals):+.2f}%")

    # 三条判读
    nxt = [s["nxt"] for s in samples if s["nxt"] is not None]
    d3 = [s["d3"] for s in samples if s["d3"] is not None]
    print(f"\n【判读】")
    if nxt:
        p = sum(1 for v in nxt if v > 0) / len(nxt) * 100
        print(f"  · 次日反弹概率 {p:.0f}%" + ("（高，可做反弹）" if p >= 65 else "（一般，别重仓赌）" if p >= 50 else "（低，不要抄底）"))
    if nxt and d3:
        p1 = sum(1 for v in nxt if v > 0) / len(nxt) * 100
        p3 = sum(1 for v in d3 if v > 0) / len(d3) * 100
        if p1 - p3 > 20:
            print(f"  · ⚠️ 次日 {p1:.0f}% → 3日后 {p3:.0f}%，**衰减明显 = 逃命波不是反转**，反弹就减仓")
        else:
            print(f"  · 次日 {p1:.0f}% → 3日后 {p3:.0f}%，衰减不明显，反弹可持续一点")
    if len(samples) < 8:
        print(f"  · ⚠️ 样本只有 {len(samples)} 个，概率不可当铁律，只作参考")
    return samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="sz399006", help="指数代码，如 sz399006 创业板 / sz399001 深成 / sh000001 上证")
    ap.add_argument("--threshold", type=float, default=-4.0, help="单日跌幅阈值（负数），默认 -4")
    ap.add_argument("--min-streak", type=int, default=0, help="要求前置连跌天数，默认 0")
    ap.add_argument("--days", type=int, default=800, help="拉多少根日线，默认 800（约 3 年）")
    ap.add_argument("--cross", default=None, help="交叉验证：symbol:threshold，如 sz399001:3")
    args = ap.parse_args()

    k = load_klines(args.symbol, args.days)
    if not k:
        print(f"❌ 拉不到 {args.symbol} 数据")
        return
    analyse(k, args.threshold, args.min_streak, label=args.symbol)

    if args.cross:
        try:
            csym, cth = args.cross.split(":")
            ck = load_klines(csym, args.days)
            if ck:
                analyse(ck, -abs(float(cth)), args.min_streak, label=f"{csym}（交叉验证）")
                print("\n➜ 两个指数结论一致才算稳；不一致说明当前环境特殊，降权使用。")
        except Exception as e:
            print(f"交叉验证失败：{e}")


if __name__ == "__main__":
    main()
