#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连板股启动前捕获扫描器（五维打分）

用法:
  python3 limitup_scan.py                 # 扫今日涨停池，输出五维打分排序
  python3 limitup_scan.py --date 20261112 # 指定日期
  python3 limitup_scan.py --min-score 70  # 只输出 ≥70 分的

五维: 基因(25) + 位置(15) + 主力(25) + 板块(20) + 大盘(15)
"""
import urllib.request
import json
import time
import sys
import argparse
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

BJ = timezone(timedelta(hours=8))
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}


def fetch(url, t=15, tries=3, enc="utf-8"):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=t).read().decode(enc, "ignore")
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(0.8)


def get_json(url, t=15, tries=3):
    r = fetch(url, t, tries)
    if not r:
        return None
    try:
        return json.loads(r)
    except Exception:
        return None


def streak_gene(symbol, days=250):
    """历史连板段长度，返回 (最大连板, 20日涨停数)"""
    r = fetch(f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{days},qfq")
    if not r:
        return 0, 0
    try:
        d = json.loads(r)["data"][symbol]
        rows = d.get("qfqday") or d.get("day") or []
        c = [float(x[2]) for x in rows]
    except Exception:
        return 0, 0
    if len(c) < 2:
        return 0, 0
    is_gem = symbol[2:].startswith(("300", "301", "688", "689"))
    th = 19.0 if is_gem else 9.0
    runs, cur = [], 0
    for i in range(1, len(c)):
        if (c[i] / c[i - 1] - 1) * 100 >= th:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    maxlb = max(runs) if runs else 0
    zt20 = sum(1 for i in range(max(1, len(c) - 20), len(c)) if (c[i] / c[i - 1] - 1) * 100 >= th)
    return maxlb, zt20


def ma_pos(symbol):
    """返回 (距MA30%, 距MA5%)"""
    r = fetch(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen=65")
    if not r:
        return None, None
    try:
        k = [float(x["close"]) for x in json.loads(r)]
    except Exception:
        return None, None
    if len(k) < 5:
        return None, None
    ma5 = sum(k[-5:]) / 5
    ma30 = sum(k[-30:]) / 30 if len(k) >= 30 else sum(k) / len(k)
    return round((k[-1] / ma30 - 1) * 100, 1), round((k[-1] / ma5 - 1) * 100, 1)


def fund_flow(symbol):
    """东财资金流：返回 (近3日主力净额亿, 近3日超大单亿, 超大单连续流入天数)
    回测依据：连续3日流入 T+3 +1.14%（胜率50%），单日流入 T+3 -0.11%；
             连续3日+涨停+累计<5亿 → T+5 +11.32%（胜率71%）
    """
    secid = ("1." if symbol.startswith("sh") else "0.") + symbol[2:]
    r = fetch(f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=90&klt=101&secid={secid}"
              f"&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f62,f63")
    if not r:
        return None, None, 0
    try:
        kl = (json.loads(r).get("data") or {}).get("klines") or []
        rows = []
        for line in kl[-6:]:
            q = line.split(",")
            if len(q) < 6:
                continue
            rows.append((float(q[1]) / 1e8, float(q[5]) / 1e8))  # (主力净额, 超大单)
        if not rows:
            return None, None, 0
        net3 = round(sum(x[0] for x in rows[-3:]), 2)
        sup3 = round(sum(x[1] for x in rows[-3:]), 2)
        # 连续流入天数（从最新往前数）
        streak = 0
        for _, sup in reversed(rows):
            if sup > 0:
                streak += 1
            else:
                break
        return net3, sup3, streak
    except Exception:
        return None, None, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYYMMDD，默认今天")
    ap.add_argument("--min-score", type=int, default=0)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    date = args.date or datetime.now(BJ).strftime("%Y%m%d")
    print(f"⏰ 连板启动前扫描 | 日期 {date} | {datetime.now(BJ):%H:%M}")

    # ===== 维度 5：大盘 =====
    zt = get_json(f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=400&sort=fbt%3Aasc&date={date}")
    pool = ((zt or {}).get("data") or {}).get("pool") or []
    if not pool:
        print("❌ 未拿到涨停池（非交易日或接口异常）")
        return

    dt_pool = get_json(f"https://push2ex.eastmoney.com/getTopicDTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=400&sort=fund%3Aasc&date={date}")
    dt_cnt = len(((dt_pool or {}).get("data") or {}).get("pool") or [])

    lb_max = max((x.get("lbc") or 1) for x in pool)
    zt_cnt = len(pool)

    # 大盘分（15 分）
    if 40 <= zt_cnt <= 80:
        mkt_pt, mkt_note = 15, "健康"
    elif 30 <= zt_cnt < 40 or 80 < zt_cnt <= 100:
        mkt_pt, mkt_note = 10, "中性"
    elif zt_cnt < 30:
        mkt_pt, mkt_note = 4, "冰点(连板难)"
    else:
        mkt_pt, mkt_note = 6, "过热(次日易炸)"
    if dt_cnt > 10:
        mkt_pt = max(0, mkt_pt - 8)
        mkt_note += " +跌停超10"

    print(f"\n【维度5·大盘】涨停 {zt_cnt} 只 / 跌停 {dt_cnt} 只 / 最高 {lb_max} 板 → {mkt_note}（{mkt_pt}/15）")

    # ===== 维度 4：板块梯队 =====
    ind_cnt = Counter(x.get("hybk") or "?" for x in pool)
    print(f"【维度4·板块】梯队TOP5: " + " | ".join(f"{k}×{v}" for k, v in ind_cnt.most_common(5)))

    # ===== 拉实时行情 =====
    codes = [x["c"] for x in pool]
    syms = [("sh" if c.startswith("6") else "sz") + c for c in codes]
    quotes = {}
    for i in range(0, len(syms), 40):
        raw = fetch("http://qt.gtimg.cn/q=" + ",".join(syms[i:i + 40]), enc="gbk")
        if not raw:
            continue
        for line in raw.strip().split("\n"):
            if '"' not in line:
                continue
            f = line.split('"')[1].split("~")
            try:
                quotes[f[2]] = {
                    "name": f[1], "px": float(f[3]), "chg": float(f[32]),
                    "to": float(f[38] or 0), "vr": float(f[49]) if len(f) > 49 and f[49] else 0,
                    "fc": float(f[44] or 0), "hi": float(f[33]), "lo": float(f[34]),
                    "b1v": float(f[10] or 0),
                }
            except Exception:
                continue
        time.sleep(0.3)

    # ===== 逐只打分 =====
    results = []
    for x in pool:
        code = x.get("c")
        q = quotes.get(code)
        if not q:
            continue
        sym = ("sh" if code.startswith("6") else "sz") + code
        ind = x.get("hybk") or "?"
        lbc = x.get("lbc") or 1
        fund = (x.get("fund") or 0) / 1e8
        zbc = x.get("zbc") or 0

        # 维度1 基因（25）
        maxlb, zt20 = streak_gene(sym)
        if maxlb >= 10:
            gene_pt = 25   # 超强基因（10+ 板历史，如锋龙 18 板）
        elif maxlb >= 5:
            gene_pt = 25
        elif maxlb >= 3:
            gene_pt = 20
        elif maxlb == 2:
            gene_pt = 12
        else:
            gene_pt = 0

        # 维度2 位置（15）
        pos30, pos5 = ma_pos(sym)
        if pos30 is None:
            pos_pt = 0
        elif -20 <= pos30 <= 10:
            pos_pt = 15
        elif 10 < pos30 <= 20:
            pos_pt = 10
        elif pos30 > 25:
            pos_pt = 0
        elif pos30 < -25:
            pos_pt = 6
        else:
            pos_pt = 8

        # 维度3 主力（25）—— 按「资金连续性」打分（回测校准）
        net3, sup3, streak = fund_flow(sym)
        if sup3 is None or streak is None:
            fund_pt = 0
        elif streak >= 3 and 0.5 <= (sup3 or 0) < 5:
            fund_pt = 25   # 最优：连续≥3日 + 中等体量（T+5 期望 +11.32%，胜率71%）
        elif streak >= 3:
            fund_pt = 22   # 连续但体量过大/过小
        elif streak == 2:
            fund_pt = 12   # 弱（T+5 仅 +0.38%）
        elif streak == 1:
            fund_pt = 6    # 单日流入（T+5 +0.02%，几乎无超额）
        else:
            fund_pt = 0
        # 炸板扣分
        if zbc >= 5:
            fund_pt = max(0, fund_pt - 10)
        # 换手率扣分：>25% 筹码不稳，<3% 一字板无换手
        if q["to"] > 25:
            fund_pt = max(0, fund_pt - 8)
        elif q["to"] < 3 and lbc >= 1:
            fund_pt = max(0, fund_pt - 4)

        # 维度4 板块（20）
        n = ind_cnt.get(ind, 0)
        if n >= 5:
            ind_pt = 20
        elif n >= 3:
            ind_pt = 15
        elif n == 2:
            ind_pt = 8
        else:
            ind_pt = 0

        total = gene_pt + pos_pt + fund_pt + ind_pt + mkt_pt

        # ===== 一票否决（硬规则，不看总分）=====
        veto = []
        if pos30 is not None and pos30 > 25:
            veto.append(f"位置过高(距MA30 {pos30:+.1f}%>25%)")
        if q["to"] > 30:
            veto.append(f"换手过高({q['to']:.1f}%>30%)")
        if zbc >= 5:
            veto.append(f"炸板{zbc}次≥5")
        if maxlb < 2:
            veto.append("无连板基因")
        if veto:
            total = 0  # 直接出局

        results.append({
            "code": code, "name": q["name"], "ind": ind, "lb": lbc,
            "fund": round(fund, 2), "to": q["to"], "vr": q["vr"], "fc": q["fc"],
            "maxlb": maxlb, "zt20": zt20, "pos30": pos30, "pos5": pos5,
            "net3": net3, "sup3": sup3, "streak": streak, "zbc": zbc,
            "gene_pt": gene_pt, "pos_pt": pos_pt, "fund_pt": fund_pt,
            "ind_pt": ind_pt, "mkt_pt": mkt_pt, "total": total,
            "veto": veto,
        })
        time.sleep(0.25)

    results.sort(key=lambda r: -r["total"])
    show = [r for r in results if r["total"] >= args.min_score][: args.top]

    print(f"\n{'名称':<10}{'代码':<8}{'行业':<9}{'板':>3}{'总分':>5}{'基因':>5}{'位置':>5}{'主力':>5}{'板块':>5}{'距MA30':>8}{'超大单3日':>10}{'炸':>3}")
    print("-" * 92)
    for r in show:
        print(f"{r['name']:<10}{r['code']:<8}{(r['ind'] or '')[:7]:<9}{r['lb']:>3}{r['total']:>5}"
              f"{r['gene_pt']:>5}{r['pos_pt']:>5}{r['fund_pt']:>5}{r['ind_pt']:>5}"
              f"{(r['pos30'] if r['pos30'] is not None else 0):>8.1f}"
              f"{(r['sup3'] if r['sup3'] is not None else 0):>10.2f}{r.get('streak',0):>5}{r['zbc']:>3}")

    print(f"\n【结论】≥70 分（可做）：{len([r for r in results if r['total']>=70])} 只")
    for r in results:
        if r["total"] >= 70:
            print(f"  ✅ {r['name']}({r['code']}) {r['lb']}板 总分{r['total']} "
                  f"| 史最大{r['maxlb']}板 | 距MA30 {r['pos30']:+.1f}% | 超大单3日{r['sup3']:+.2f}亿")
    if not any(r["total"] >= 70 for r in results):
        print("  ⚠️ 今日无 ≥70 分标的 —— 不建议做连板博弈，等更好的机会")

    vetoed = [r for r in results if r.get("veto")]
    if vetoed:
        print(f"\n【一票否决】{len(vetoed)} 只")
        for r in vetoed[:8]:
            print(f"  ❌ {r['name']}({r['code']}) {r['lb']}板 | {', '.join(r['veto'])}")

    # 主力意图阶段推断
    print("\n【主力意图阶段】")
    for r in show[:6]:
        if r["sup3"] is not None and r["sup3"] > 0.3:
            stage = "② 拉升期（大资金在进）"
        elif r["sup3"] is not None and r["sup3"] > 0:
            stage = "① 建仓/洗盘（小幅流入）"
        elif r["zbc"] >= 5:
            stage = "③ 派发（炸板多+资金流出）"
        elif r["sup3"] is not None and r["sup3"] < -0.3:
            stage = "④ 崩塌（大资金撤离）"
        else:
            stage = "？ 中性"
        print(f"  {r['name']:<10}{r['lb']}板 → {stage}")

    print("\n⚠️ 仅供参考，不构成投资建议。")


if __name__ == "__main__":
    main()
