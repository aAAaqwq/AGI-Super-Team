#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""竞价后持仓做T方案数据采集（9:26 跑，配 references/t-plus-zero-and-order-placement.md）

读 $POSITIONS_FILE（默认 ./positions.json），对每只持仓输出：
  竞价开盘价/涨幅、竞价量/量比、昨收、昨日高低与 VWAP、MA5/10/20、近10日振幅、止损位

用法:
  python3 auction_t.py
  # 或作为 cron 的 script= 参数，9:26 一次性触发，输出交给 agent 出方案

⚠️ 关键坑（本脚本已处理）：
  腾讯 f[6]=成交量(手)、f[37]=成交额(万元)
  VWAP = (f[37]*10000)/(f[6]*100)，漏掉 /100 会得到 1746.16 这种离谱值
"""
import os
import urllib.request
import json
from datetime import datetime, timezone, timedelta

BJ = timezone(timedelta(hours=8))
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
POS_FILE = os.environ.get("POSITIONS_FILE", "positions.json")


def gbk(url, t=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=t).read().decode("gbk", "ignore")


def utf8(url, t=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=t).read().decode("utf-8", "ignore")


def ma_and_levels(sym):
    """近45日：MA5/10/20 + 昨日 VWAP(近似) + 近10日均振幅"""
    r = utf8(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
             f"?symbol={sym}&scale=240&ma=no&datalen=45")
    if not r:
        return None
    k = [{"d": x["day"], "o": float(x["open"]), "h": float(x["high"]), "l": float(x["low"]),
          "c": float(x["close"]), "v": float(x["volume"]) / 100} for x in json.loads(r)]
    c = [x["c"] for x in k]
    amps = []
    for i in range(max(1, len(k) - 10), len(k)):
        if k[i - 1]["c"]:
            amps.append((k[i]["h"] - k[i]["l"]) / k[i - 1]["c"] * 100)
    y = k[-1]
    return {
        "ma5": sum(c[-5:]) / 5, "ma10": sum(c[-10:]) / 10,
        "ma20": sum(c[-20:]) / 20 if len(c) >= 20 else sum(c) / len(c),
        "y_high": y["h"], "y_low": y["l"], "y_close": y["c"], "y_open": y["o"],
        "vwap": (y["h"] + y["l"] + y["c"]) / 3,   # K线无额，用典型价近似
        "avg_amp": sum(amps) / len(amps) if amps else 0,
        "max_amp": max(amps) if amps else 0,
    }


def main():
    now = datetime.now(BJ)
    print(f"⏰ 竞价做T方案 | {now:%Y-%m-%d %H:%M}（{now.strftime('%A')}）")
    print("=" * 88)

    d = json.load(open(POS_FILE, encoding="utf-8"))
    poss = d.get("positions", [])
    if not poss:
        print("❌ positions.json 无持仓")
        return

    syms = []
    for p in poss:
        syms.append(p.get("sym") or (("sh" if str(p["code"]).startswith("6") else "sz") + str(p["code"])))
    raw = gbk("http://qt.gtimg.cn/q=" + ",".join(syms))

    for line in raw.strip().split("\n"):
        if '"' not in line:
            continue
        f = line.split('"')[1].split("~")
        code = f[2]
        p = next((x for x in poss if str(x["code"]) == code), None)
        if not p:
            continue
        nm, cost, hold = p["name"], float(p["cost"]), int(p["shares"])
        avail = int(p.get("avail", hold))

        px = float(f[3]); prev = float(f[4])
        op = float(f[5]) if f[5] else 0
        vol_hand = float(f[6]) if f[6] else 0
        amt_wan = float(f[37]) if f[37] else 0
        gap = (op / prev - 1) * 100 if (op and prev) else 0
        chg = (px / prev - 1) * 100 if prev else 0
        vr = float(f[49]) if len(f) > 49 and f[49] else 0
        # ⭐ 正确的 VWAP（单位坑见文件头）
        vwap_today = (amt_wan * 10000) / (vol_hand * 100) if vol_hand else 0

        ml = ma_and_levels(p.get("sym") or (("sh" if str(code).startswith("6") else "sz") + str(code)))

        print(f"\n【{nm}】{code}")
        print(f"  持仓 {hold} 股（可用 {avail}）｜成本 {cost:.3f}｜浮亏 {(px/cost-1)*100:+.2f}%")
        print(f"  🔔 竞价：开盘 {op:.3f}（{gap:+.2f}%）｜现价 {px:.3f}（{chg:+.2f}%）｜昨收 {prev:.3f}")
        print(f"  竞价/当日量 {vol_hand/10000:.1f} 万手｜量比 {vr:.2f}｜当日VWAP≈{vwap_today:.3f}" if vwap_today else "")
        if ml:
            print(f"  昨日：开{ml['y_open']:.3f} 高{ml['y_high']:.3f} 低{ml['y_low']:.3f} 收{ml['y_close']:.3f}｜典型均价≈{ml['vwap']:.3f}")
            print(f"  均线：MA5 {ml['ma5']:.3f}｜MA10 {ml['ma10']:.3f}｜MA20 {ml['ma20']:.3f}")
            print(f"  近10日振幅：均 {ml['avg_amp']:.2f}%｜最大 {ml['max_amp']:.2f}%")
            print(f"  ➜ MA10 距现价 {(px/ml['ma10']-1)*100:+.2f}%（破 MA10 不买回）")
            # 净收益门槛提示
            lots = min(avail, (hold // 2) if hold >= 200 else hold)
            fee = 0.0003 * 2 + 0.0005
            net3 = lots * px * 0.03 - lots * px * fee
            print(f"  ➜ 做 {lots} 股赚 3% 净收益 ≈ {net3:.0f} 元 {'✅ 值得' if net3 >= 30 else '❌ <30 元，不做'}")
        print(f"  止损位 {p.get('stop','-')}（{p.get('stop_note','')}）")

    print("\n" + "=" * 88)
    print("【摘要】按 references/t-plus-zero-and-order-placement.md 5b.4 的条件表出方案：")
    print("  低开>3%→正T | 平开±2%→反T | 高开>2%→减仓不买回 | 破MA10/破昨低→减仓不买回")


if __name__ == "__main__":
    main()
