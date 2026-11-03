#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四维共振分析（时间轴 / 结构轴 / 节奏轴 / 量价轴）

用法：
    python3 volume_resonance.py 600838 301101 603528
    python3 volume_resonance.py 600838 --date 20261023      # 指定涨停池日期
    python3 volume_resonance.py 600838 --json               # 输出 JSON

数据源（全部免费公开，无需 key）：
    ① 时间轴/量价轴：腾讯 fqkline（前复权日K，120 日）
    ② 结构轴：东财涨停池 getTopicZTPool（含 hybk 行业）+ push2 个股行业 f127
    ③ 节奏轴：腾讯 minute 分时（当日累计成交额差分）
"""
import sys
import json
import time
import argparse
import urllib.request
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
BJT = timezone(timedelta(hours=8))


# ---------------------------------------------------------------- 基础工具
def fetch(url, timeout=25, tries=3, gbk=False):
    last = None
    for i in range(tries):
        try:
            raw = urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=timeout).read()
            return raw.decode("gbk", "ignore") if gbk else raw.decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            if i < tries - 1:
                time.sleep(1)
    raise RuntimeError("fetch failed: %s (%s)" % (url, last))


def prefix(code):
    """6 位代码 → 带市场前缀"""
    if code.startswith(("sh", "sz", "bj")):
        return code
    if code.startswith(("6", "9", "5")):
        return "sh" + code
    if code.startswith(("4", "8")):
        return "bj" + code
    return "sz" + code


def code6(code):
    return code[-6:]


def secid(code):
    """东财 secid：1=沪 0=深"""
    c = code6(code)
    return ("1." if c.startswith(("6", "9", "5")) else "0.") + c


def bj_now():
    return datetime.now(BJT)


# ---------------------------------------------------------------- 行情快照
def quote(code):
    f = fetch("http://qt.gtimg.cn/q=" + prefix(code), gbk=True).split('"')[1].split("~")
    return {
        "name": f[1],
        "price": float(f[3]),
        "prev_close": float(f[4]),
        "chg_pct": float(f[32]),
        "vol": float(f[6]),              # 手
        "ts": f[30],
        "turnover": f[38],
    }


def industry(code):
    """行业 + 概念。主源 push2 f127；push2 抽风时降级 F10 核心题材（BOARD_TYPE=行业）。"""
    try:
        d = json.loads(fetch(
            "https://push2.eastmoney.com/api/qt/stock/get?ut=fa5fd1943c7b386f172d6893dbfba10b"
            "&fltt=2&invt=2&secid=%s&fields=f57,f58,f127,f128,f129" % secid(code),
            timeout=15, tries=2)).get("data") or {}
        if d.get("f127"):
            return d["f127"], d.get("f129") or ""
    except Exception:  # noqa: BLE001
        pass
    # 降级：东财 F10 核心题材
    c = code6(code)
    suffix = ".SH" if prefix(code).startswith("sh") else (".BJ" if prefix(code).startswith("bj") else ".SZ")
    u = ("https://datacenter.eastmoney.com/securities/api/data/v1/get"
         "?reportName=RPT_F10_CORETHEME_BOARDTYPE"
         "&columns=SECUCODE,BOARD_CODE,BOARD_NAME,BOARD_TYPE"
         "&filter=(SECUCODE%%3D%%22%s%s%%22)&pageSize=60&source=HSF10&client=PC" % (c, suffix))
    data = (json.loads(fetch(u)).get("result") or {}).get("data") or []
    ind = next((x["BOARD_NAME"] for x in data if x.get("BOARD_TYPE") == "行业"), "")
    concepts = "/".join(x["BOARD_NAME"] for x in data
                        if x.get("BOARD_TYPE") not in ("行业", None))[:60]
    return ind, concepts


# ---------------------------------------------------------------- ① 时间轴
def axis_time(code):
    c = prefix(code)
    k = json.loads(fetch(
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=%s,day,,,120,qfq" % c))
    node = k["data"][c]
    rows = node.get("qfqday") or node.get("day")
    v = [float(r[5]) for r in rows]
    today = v[-1]
    m5 = sum(v[-6:-1]) / 5
    m20 = sum(v[-21:-1]) / 20
    m60 = sum(v[-61:-1]) / 60
    r5, r20, r60 = today / m5, today / m20, today / m60
    if r5 > 7:
        judge, score = "🔴🔴 极端天量（透支/出货嫌疑）", -2
    elif r5 > 3:
        judge, score = "🔴 天量（分歧极大）", -1
    elif r5 > 1.5:
        judge, score = "🟡 放量", 1
    elif r5 > 0.9:
        judge, score = "🟢 平量（锁仓/健康）", 1
    else:
        judge, score = "🟢 缩量（惜售/高控盘）", 1
    chg_k = (float(rows[-1][2]) / float(rows[-2][2]) - 1) * 100
    return {"date": rows[-1][0], "vol_wan": today / 1e4, "r5": r5, "r20": r20,
            "r60": r60, "chg_k": chg_k, "judge": judge, "score": score}


# ---------------------------------------------------------------- ② 结构轴
def zt_pool(date):
    for ut in ("7eea3edcaed734bea9cbfc24409ed989", "fa5fd1943c7b386f172d6893dbfba10b"):
        u = ("https://push2ex.eastmoney.com/getTopicZTPool?ut=%s&dpt=wz.ztzt"
             "&Pageindex=0&pagesize=300&sort=fbt%%3Aasc&date=%s" % (ut, date))
        try:
            j = json.loads(fetch(u, timeout=20, tries=2))
            pool = (j.get("data") or {}).get("pool") or []
            if pool:
                return pool
        except Exception:  # noqa: BLE001
            continue
    return []


def axis_structure(code, pool, ind):
    """hybk 是 4 字截断行业名，用 startswith 双向匹配"""
    import difflib
    def _match(hy, ind):
        if not hy or not ind:
            return False
        if ind.startswith(hy) or hy.startswith(ind) or ind[:2] == hy[:2]:
            return True
        # 0.7 才可信：文娱用品/文化用品=0.75 ✅；个护用品/家居用品=0.5 ❌ 会误算
        return difflib.SequenceMatcher(None, hy, ind).ratio() >= 0.7
    same = [p for p in pool if _match(p.get("hybk") or "", ind)]
    n = len(same)
    if n <= 1:
        judge, score = "🔴 独苗（板块无托底）", -2
    elif n <= 2:
        judge, score = "🟡 板块偏小（%d 只）" % n, 0
    elif n <= 4:
        judge, score = "🟡 板块一般（%d 只）" % n, 1
    else:
        judge, score = "🟢🟢 有梯队（%d 只）" % n, 2
    return {"industry": ind, "zt_count": n, "peers": [p.get("n") for p in same],
            "judge": judge, "score": score}


# ---------------------------------------------------------------- ③ 节奏轴
def axis_rhythm(code):
    c = prefix(code)
    j = json.loads(fetch("https://web.ifzq.gtimg.cn/appstock/app/day/query?code=" + c))
    blocks = (j["data"][c].get("data") or [])
    blocks = sorted(blocks, key=lambda b: b.get("date", ""), reverse=True)
    today = bj_now().strftime("%Y%m%d")
    rows, day, is_today = [], None, False
    for b in blocks:                      # 选最近一个有成交的交易日
        rs = b.get("data") or []
        if len(rs) > 1 and float(rs[-1].split()[3] or 0) > 0:
            rows, day = rs, b.get("date")
            is_today = (day == today)
            break
    if not rows:
        return {"judge": "⚪ 分时无数据", "score": 0, "segs": [], "total_yi": 0,
                "pct_first30": 0, "day": None, "is_today": False}
    cum, px = {}, {}
    for r in rows:
        p_ = r.split()
        cum[p_[0]] = float(p_[3])         # 累计成交额（元）
        px[p_[0]] = float(p_[1])
    marks = ["0930", "1000", "1030", "1100", "1130", "1330", "1400", "1430", "1500"]
    segs, prev_t = [], "0930"
    for t in marks[1:]:
        if t in cum and prev_t in cum:
            segs.append((prev_t + "-" + t, cum[t] - cum[prev_t]))
        if t in cum:
            prev_t = t
    last_key = max(cum)
    total = cum[last_key]
    first30 = next((v for k, v in segs if k.startswith("0930")), 0.0)
    pct_first = first30 / total * 100 if total else 0.0
    if pct_first >= 50:
        judge, score = "🟢 早盘打完 %d%%，之后无量（封死锁仓）" % pct_first, 2
    elif pct_first >= 35:
        judge, score = "🟡 早盘 %d%%（偏集中）" % pct_first, 1
    else:
        judge, score = "🟡 早盘仅 %d%%，全天分散" % pct_first, 0
    return {"day": day, "is_today": is_today, "total_yi": total / 1e8, "segs": segs,
            "pct_first30": pct_first, "last_px": px[last_key],
            "judge": judge, "score": score}


# ---------------------------------------------------------------- ④ 量价轴
def axis_price_volume(chg, r5):
    up = chg > 0
    if up and r5 > 3:
        judge, score = "⚠️ 天量上涨（分歧极大）", -1
    elif up and r5 >= 1.2:
        judge, score = "✅ 放量上涨（健康进攻）", 2
    elif up and r5 >= 0.9:
        judge, score = "🟡 平量上涨", 1
    elif up:
        judge, score = "🟢 缩量上涨（高控盘锁仓）", 2
    elif r5 > 1.2:
        judge, score = "🔴 放量下跌（派发）", -2
    elif r5 < 0.8:
        judge, score = "🟠 缩量下跌（看是否洗盘）", -1
    else:
        judge, score = "🟡 平量下跌", -1
    return {"chg": chg, "r5": r5, "judge": judge, "score": score}


# ---------------------------------------------------------------- 汇总
def resonance(res):
    """共振度 = 四维同向程度；不一致（有正有负）比低分更危险"""
    s = [res["time"]["score"], res["structure"]["score"],
         res["rhythm"]["score"], res["pv"]["score"]]
    pos, neg = sum(1 for x in s if x > 0), sum(1 for x in s if x < 0)
    total = sum(s)
    if neg == 0:
        consistency, label = "🟢 四维一致（全部指向多头/锁仓）", "共振"
    elif pos == 0:
        consistency, label = "🔴 四维一致向下", "反向共振"
    elif abs(pos - neg) >= 3:
        consistency, label = "🟢 方向基本一致（%d正%d负）" % (pos, neg), "弱共振"
    else:
        consistency, label = "🔴 维度互相矛盾（%d正%d负）→ 单点爆发，不是共振" % (pos, neg), "矛盾"
    return {"scores": s, "total": total, "pos": pos, "neg": neg,
            "consistency": consistency, "label": label,
            "star": "⭐" * min(5, max(1, round((total + 6) / 2)))}


def analyze(codes, pool_date=None, intraday=False):
    out = []
    date = pool_date or bj_now().strftime("%Y%m%d")
    try:
        pool = zt_pool(date)
    except Exception as e:  # noqa: BLE001
        print("⚠️ 涨停池拉取失败(%s)，结构轴降级为 -" % e, file=sys.stderr)
        pool = []
    today = bj_now().strftime("%Y%m%d")
    for code in codes:
        q = quote(code)
        ind, concept = industry(code)
        t = axis_time(code)
        # 盘中判定：行情时间戳是今天且已有成交 → 今日量/涨跌未完成
        intraday = (q["ts"][:8] == today and q["vol"] > 0)
        chg = q["chg_pct"] if intraday else t["chg_k"]
        st = axis_structure(code, pool, ind) if pool else {
            "industry": ind, "zt_count": None, "peers": [],
            "judge": "⚪ 涨停池不可用", "score": 0}
        try:
            rh = axis_rhythm(code)
        except Exception as e:  # noqa: BLE001
            rh = {"judge": "⚪ 分时不可用(%s)" % str(e)[:40], "score": 0,
                  "segs": [], "total_yi": 0, "pct_first30": 0}
        pv = axis_price_volume(chg, t["r5"])
        r = {"code": code6(code), "name": q["name"], "price": q["price"],
             "chg": chg, "intraday": intraday, "concept": concept, "quote_ts": q["ts"],
             "time": t, "structure": st, "rhythm": rh, "pv": pv}
        r.update(resonance(r))
        out.append(r)
    return out


def render(results):
    print("=" * 96)
    print("四维共振分析  |  北京时间 %s" % bj_now().strftime("%Y-%m-%d %H:%M"))
    if any(r.get("intraday") for r in results):
        print("⚠️ 盘中口径：今日量能/涨跌未完成，时间轴与量价轴须按【同时段】折算后再判，"
              "节奏轴为当日分时（可用于判断边际强弱）")
    print("=" * 96)
    for r in results:
        print("\n【%s %s】%.2f（%+.2f%%）  概念：%s" % (
            r["name"], r["code"], r["price"], r["chg"], r["concept"][:40]))
        t, st, rh, pv = r["time"], r["structure"], r["rhythm"], r["pv"]
        print("  ① 时间轴  %s" % t["date"])
        print("     量 %.1f万手 | /5日 %.2f | /20日 %.2f | /60日 %.2f → %s"
              % (t["vol_wan"], t["r5"], t["r20"], t["r60"], t["judge"]))
        print("  ② 结构轴  行业 %s" % (st["industry"] or "?"))
        if st["zt_count"] is not None:
            print("     同行业涨停 %d 只%s → %s" % (
                st["zt_count"],
                ("（" + "、".join(x for x in st["peers"] if x) + "）") if st["peers"] else "",
                st["judge"]))
        else:
            print("     %s" % st["judge"])
        print("  ③ 节奏轴  %s 全天 %.2f 亿" % (rh.get("day", "-"), rh.get("total_yi", 0)))
        for seg, amt in rh.get("segs", []):
            print("     %-11s %6.2f 亿  %5.1f%%" % (
                seg, amt / 1e8,
                amt / (rh["total_yi"] * 1e8) * 100 if rh.get("total_yi") else 0))
        print("     → %s" % rh["judge"])
        print("  ④ 量价轴  涨跌 %+.2f%% × 量比 %.2f → %s" % (pv["chg"], pv["r5"], pv["judge"]))
        print("  ── 共振度 %d（%d正%d负）%s  %s  %s" % (
            r["total"], r["pos"], r["neg"], r["star"], r["label"], r["consistency"]))
    print("\n" + "=" * 96)
    print("排序（共振度）：")
    for i, r in enumerate(sorted(results, key=lambda x: -x["total"]), 1):
        print("  %d. %s %s  %d 分  %s  %s" % (
            i, r["name"], r["code"], r["total"], r["label"], r["consistency"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="+")
    ap.add_argument("--date", help="涨停池日期 YYYYMMDD（默认今天）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = analyze(a.codes, a.date)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    else:
        render(res)


if __name__ == "__main__":
    main()
