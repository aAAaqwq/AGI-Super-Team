#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真金三连 · 每日自动扫描（9:00 盘前 + 9:28 竞价后）

回测校准（599 只含小盘 / 4,531 信号 / 123 交易日）：
  · 流通市值 ≥50 亿才有效（小盘 <50亿 T+5 仅 +1.34%，胜率 41%）
  · 中小 50-120 亿 + 热板 → T+5 +9.58%，胜率 62%
  · 中大盘 >120 亿 + 热板 → T+5 +9.17%，胜率 77%（胜率最高）
  · 连续≥3日超大单流入 + 涨停 + 3日累计 0.5~5 亿
  · 所属行业当日热度 TOP20%

用法:
  python3 golden_triple.py --mode pre       # 9:00 盘前（扫上一交易日涨停池）
  python3 golden_triple.py --mode auction   # 9:28 竞价后（加竞价强度判断）
  python3 golden_triple.py --mode pre --date 20261117
"""
import urllib.request
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BJ = timezone(timedelta(hours=8))
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}


def fetch(url, t=20, tries=3, enc="utf-8"):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=t).read().decode(enc, "ignore")
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.7)


def last_trade_date():
    """往前找最近一个有涨停数据的交易日（最多回退5天）"""
    d = datetime.now(BJ)
    for k in range(0, 6):
        s = (d - timedelta(days=k)).strftime("%Y%m%d")
        r = fetch(f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989"
                  f"&dpt=wz.ztzt&Pageindex=0&pagesize=10&sort=fbt%3Aasc&date={s}", t=10)
        if not r:
            continue
        try:
            p = (json.loads(r).get("data") or {}).get("pool") or []
            if p:
                return s
        except Exception:
            pass
    return None


def zt_pool(date):
    r = fetch(f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989"
              f"&dpt=wz.ztzt&Pageindex=0&pagesize=400&sort=fbt%3Aasc&date={date}", t=25)
    if not r:
        return []
    try:
        return (json.loads(r).get("data") or {}).get("pool") or []
    except Exception:
        return []


def flow_of(code):
    """东财 fflow：返回 (连续天数, 3日累计亿)"""
    secid = ("1." if code.startswith("6") else "0.") + code
    r = fetch(f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=12&klt=101&secid={secid}"
              f"&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f62,f63", t=12)
    if not r:
        return 0, 0.0
    try:
        kl = (json.loads(r).get("data") or {}).get("klines") or []
    except Exception:
        return 0, 0.0
    sup = []
    for line in kl:
        p = line.split(",")
        if len(p) > 5:
            try:
                sup.append(float(p[5]) / 1e8)
            except Exception:
                pass
    if not sup:
        return 0, 0.0
    streak = 0
    for v in reversed(sup):
        if v > 0:
            streak += 1
        else:
            break
    return streak, round(sum(sup[-3:]), 3)


def quotes(codes):
    """腾讯实时：返回 {code: {px, prev, op, hi, lo, chg, vr, to, mc, out}}"""
    out = {}
    syms = [("sh" if c.startswith("6") else "sz") + c for c in codes]
    for i in range(0, len(syms), 40):
        raw = fetch("http://qt.gtimg.cn/q=" + ",".join(syms[i:i + 40]), enc="gbk")
        if not raw:
            continue
        for line in raw.strip().split("\n"):
            if '"' not in line:
                continue
            f = line.split('"')[1].split("~")
            try:
                ip = float(f[7]) if f[7] else 0
                o2 = float(f[8]) if f[8] else 0
                out[f[2]] = {
                    "nm": f[1], "px": float(f[3]), "prev": float(f[4]),
                    "op": float(f[5]) if f[5] else 0, "hi": float(f[33]), "lo": float(f[34]),
                    "chg": float(f[32]), "to": float(f[38] or 0),
                    "vr": float(f[49]) if len(f) > 49 and f[49] else 0,
                    "mc": float(f[44] or 0),
                    "out": (o2 / (ip + o2) * 100) if (ip + o2) > 0 else 0,
                }
            except Exception:
                continue
        time.sleep(0.25)
    return out


def ind_heat():
    """行业热度分位（用当日行业板块涨幅排名）"""
    r = fetch("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=120&po=1&np=1&fltt=2&invt=2"
              "&fid=f3&fs=m:90+t:2&fields=f3,f14", t=20)
    if not r:
        return {}
    try:
        items = (json.loads(r).get("data") or {}).get("diff") or []
    except Exception:
        return {}
    vals = [(x.get("f14") or "", x.get("f3") or 0) for x in items]
    if not vals:
        return {}
    chgs = sorted(v for _, v in vals)
    n = len(chs) if (chs := chgs) else 1
    return {nm: sum(1 for x in chgs if x <= v) / n * 100 for nm, v in vals}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["pre", "auction"], default="pre")
    ap.add_argument("--date", help="手动指定扫描日期 YYYYMMDD")
    ap.add_argument("--amount-max", type=float, default=5.0)
    args = ap.parse_args()

    now = datetime.now(BJ)
    date = args.date or last_trade_date()
    mode_cn = "盘前扫描" if args.mode == "pre" else "竞价确认"

    print(f"⏰ 真金三连 · {mode_cn} | {now:%Y-%m-%d %H:%M} ({now.strftime('%A')})")
    print(f"   扫描日期：{date}（上一交易日涨停池）")
    print("=" * 100)

    if not date:
        print("❌ 未找到可用交易日")
        return

    pool = zt_pool(date)
    if not pool:
        print("❌ 涨停池为空")
        return
    print(f"涨停池 {len(pool)} 只，逐个核验（连续流入 / 体量 / 市值 / 热度）...\n")

    heat = ind_heat()
    # 同行业涨停数（作为热度主指标，比行业涨幅分位更可靠）
    from collections import Counter as _C
    ind_zt_count = _C((x.get("hybk") or "?") for x in pool)
    ind_zt_rank = {}
    if ind_zt_count:
        mx = max(ind_zt_count.values())
        for k, v in ind_zt_count.items():
            ind_zt_rank[k] = v / mx * 100 if mx else 0
    codes = [x["c"] for x in pool]
    q = quotes(codes)

    hits = []
    for x in pool:
        code = x.get("c")
        info = q.get(code)
        if not info:
            continue
        streak, cum3 = flow_of(code)
        ind = x.get("hybk") or "?"
        mc = info["mc"]
        h1 = ind_zt_rank.get(ind)          # 同行业涨停数分位
        h2 = heat.get(ind)                 # 行业涨幅分位
        h = max([x for x in (h1, h2) if x is not None], default=None)
        # 分级
        tier = "小盘" if mc < 50 else ("中小" if mc < 120 else "中大盘")
        graded = None
        if streak >= 3 and 0.5 <= cum3 < args.amount_max and mc >= 50:
            graded = "⭐真金三连"
            if h is not None and h >= 80:
                graded = "⭐⭐真金三连·热板"
        elif streak >= 3 and mc < 50:
            graded = "🔴小盘(信号失效)"
        elif streak >= 3:
            graded = "🟡体量偏离"
        elif streak == 2:
            graded = "🟠仅2日"
        else:
            graded = "❌单日"
        hits.append({"code": code, "nm": info["nm"], "ind": ind, "lb": x.get("lbc") or 1,
                     "streak": streak, "cum3": cum3, "mc": mc, "tier": tier,
                     "heat": h, "fund": (x.get("fund") or 0) / 1e8, "zbc": x.get("zbc") or 0,
                     "px": info["px"], "prev": info["prev"], "op": info["op"],
                     "vr": info["vr"], "to": info["to"], "out": info["out"],
                     "graded": graded})
        time.sleep(0.12)

    hits.sort(key=lambda r: (0 if "⭐⭐" in r["graded"] else 1 if "⭐" in r["graded"] else 2, -r["streak"]))
    q["__hits__"] = hits

    print(f"{'名称':<10}{'代码':<8}{'行业':<8}{'板':>3}{'连流':>5}{'3日亿':>8}{'市值':>7}{'热度':>5}{'同板':>4}{'封单':>6}  分级")
    print("-" * 100)
    for h in hits:
        if h["graded"].startswith("❌"):
            continue
        hv = f"{h['heat']:.0f}%" if h["heat"] is not None else "—"
        nzt = ind_zt_count.get(h['ind'], 0)
        print(f"{h['nm']:<10}{h['code']:<8}{h['ind'][:6]:<8}{h['lb']:>3}{h['streak']:>5}"
              f"{h['cum3']:>8.2f}{h['mc']:>7.0f}{hv:>5}{nzt:>3}只{h['fund']:>6.2f}  {h['graded']}")

    stars = [h for h in hits if h["graded"].startswith("⭐⭐")]
    base = [h for h in hits if "真金三连" in h["graded"]]

    print(f"\n{'='*100}")

    if args.mode == "pre":
        if stars:
            print(f"✅ 【真金三连·热板】命中 {len(stars)} 只（首选）：")
            for h in stars:
                print(f"   {h['nm']}({h['code']}) {h['lb']}板 | 连续{h['streak']}日 {h['cum3']:+.2f}亿 | "
                      f"{h['tier']}{h['mc']:.0f}亿 | 热度{(f'{h[chr(39)+chr(39)]}') if False else (f'{h["heat"]:.0f}%' if h['heat'] is not None else '—')} | 封单{h['fund']:.2f}亿")
            print(f"   → 回测期望：{h['tier']} T+5 +9.58%（胜率62%）/ 大盘 +9.17%（胜率77%）")
        if base and len(base) > len(stars):
            others = [h for h in base if h not in stars]
            print(f"\n⭐ 【真金三连】无热板 {len(others)} 只（次选）：")
            for h in others:
                hv = f"{h['heat']:.0f}%" if h["heat"] is not None else "—"
                print(f"   {h['nm']}({h['code']}) {h['lb']}板 | 连续{h['streak']}日 {h['cum3']:+.2f}亿 | "
                      f"{h['tier']}{h['mc']:.0f}亿 | 热度{hv}")
        if not base:
            print("⚠️ 今日无「真金三连」命中 → 不做连板博弈")
        print(f"\n📋 9:28 竞价后会再推一次，判断是否高开可接力。")
    else:
        # 竞价模式：加竞价强度
        print("📊 竞价强度判断（9:28）")
        if not base:
            print("⚠️ 无候选，无需判断")
        for h in base:
            gap = (h["op"] / h["prev"] - 1) * 100 if h["prev"] else 0
            # 判断
            if gap >= 9.5:
                verdict = "🔴 一字板，买不进 → 放弃"
            elif 3 <= gap < 9.5:
                verdict = "🟢 高开3-9.5%，可接力（仓位1-2成，止损昨收盘）"
            elif 0 <= gap < 3:
                verdict = "🟡 小幅高开，观察10分钟不破昨收可小仓"
            elif -3 < gap < 0:
                verdict = "🟠 低开，等企稳（不破昨低再考虑）"
            else:
                verdict = "🔴 低开>3%，放弃"
            print(f"\n   {h['nm']}({h['code']}) {h['lb']}板")
            print(f"     昨收 {h['prev']:.2f} → 竞价开 {h['op']:.2f}（{gap:+.2f}%）")
            print(f"     量比 {h['vr']:.2f} | 外盘 {h['out']:.1f}% | 连流{h['streak']}日 {h['cum3']:+.2f}亿")
            print(f"     ➜ {verdict}")

    print("\n⚠️ 仅供参考，不构成投资建议。数据源：东财 fflow（含市值≥50亿过滤）")


if __name__ == "__main__":
    main()
