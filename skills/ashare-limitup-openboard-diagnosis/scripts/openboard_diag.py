#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""涨停开板性质诊断 —— 判断是分歧洗盘还是出货。

用法:
    python3 openboard_diag.py sh603089 sz002931 sh603901

输出: 涨停价 / 是否一字 / 封板前震荡 / 开板段(起止·时长·最低·回落%) /
      炸板次数 / 封单占流通比 / 全天内外盘 / 分歧分(0-4)
数据源: 腾讯行情 + 腾讯分时 + 腾讯日K + 东财涨停池
"""
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}


def fetch(url, gbk=False):
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=20, context=CTX).read()
    return raw.decode("gbk", "ignore") if gbk else raw.decode("utf-8", "ignore")


def prev_close(code):
    """取昨收（日K最后一根若已是今天则往前取一根）"""
    j = json.loads(fetch(f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,30,qfq"))
    d = j["data"][code]
    rows = d.get("qfqday") or d.get("day")
    today = datetime.now(BJ).strftime("%Y-%m-%d")
    if rows[-1][0] == today:
        return float(rows[-2][2])
    return float(rows[-1][2])


def snapshot(code):
    raw = fetch(f"http://qt.gtimg.cn/q={code}", gbk=True).split("=")[1].strip('";\n').split("~")
    f = {i: v for i, v in enumerate(raw)}
    return {
        "name": f[1], "price": float(f[3]), "prec": float(f[4]),
        "inner": float(f[7]), "outer": float(f[8]),
        "bid1_price": f[9], "bid1_vol": float(f[10] or 0),
        "float_mv": float(f[44] or 0) * 1e8,
        "turnover": f[38], "vol_ratio": f[49], "time": f[30],
    }


def minute_segments(code, zt):
    """返回 (是否一字未开, 低于涨停价的连续分钟段列表)"""
    j = json.loads(fetch(f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={code}"))
    rows = j["data"][code]["data"]["data"]
    parsed = []
    for r in rows:
        p = r.split()
        if len(p) >= 2:
            parsed.append((p[0], float(p[1])))
    below = [(t, px) for t, px in parsed if px < zt - 0.001]
    if not below:
        return True, []
    segs, cur = [], [below[0]]
    for i in range(1, len(below)):
        gap = int(below[i][0]) - int(cur[-1][0])
        if 0 < gap <= 2:  # 允许 11:30 -> 13:00 的跨午休
            cur.append(below[i])
        else:
            segs.append(cur)
            cur = [below[i]]
    segs.append(cur)
    out = []
    for s in segs:
        low = min(px for _, px in s)
        out.append({"start": s[0][0], "end": s[-1][0], "mins": len(s),
                    "low": low, "drop_pct": (low / zt - 1) * 100})
    return False, out


def zt_pool(date_str):
    url = ("https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989"
           f"&dpt=wz.ztzt&Pageindex=0&pagesize=400&sort=fbt%3Aasc&date={date_str}")
    try:
        return {p["c"]: p for p in json.loads(fetch(url))["data"]["pool"]}
    except Exception:
        return {}


def fmt_t(t):
    t = str(t).strip()
    if t.isdigit():
        t = t.zfill(6)
        return f"{t[:2]}:{t[2:4]}:{t[4:6]}"
    return "-"


def diag(code):
    pc = prev_close(code)
    limit = 1.2 if code.startswith(("sz30", "sh68")) else 1.1
    zt = round(pc * limit, 2)
    snap = snapshot(code)
    yizi, segs = minute_segments(code, zt)

    seal_yi = snap["bid1_vol"] * 100 * snap["price"] / 1e8
    shares = snap["float_mv"] / snap["price"] if snap["price"] else 0
    seal_pct = snap["bid1_vol"] * 100 / shares * 100 if shares else 0
    total_ip = snap["inner"] + snap["outer"]
    outer_ratio = snap["outer"] / total_ip * 100 if total_ip else 0

    info = zt_pool(datetime.now(BJ).strftime("%Y%m%d")).get(code[2:], {})
    fbt_raw = info.get("fbt", "")
    fbt = str(fbt_raw).zfill(6) if str(fbt_raw).isdigit() else ""
    zbc = info.get("zbc", "?")
    lbc = info.get("lbc", "?")

    # 首封之前的震荡 ≠ 开板；只有首封之后的段才是真开板
    pre_seal = [s for s in segs if fbt and s["end"] < fbt[:4]]
    post_seal = [s for s in segs if not (fbt and s["end"] < fbt[:4])]

    print(f"\n=== {snap['name']} {code}  涨停价 {zt} (昨收 {pc}) ===")
    print(f"  收盘 {snap['price']}  换手 {snap['turnover']}%  量比 {snap['vol_ratio']}"
          f"  连板 {lbc}  首封 {fmt_t(fbt_raw)}  炸板 {zbc}次")
    seal_level = "极强" if seal_pct > 3 else "强" if seal_pct > 1.5 else "一般" if seal_pct > 0.5 else "弱(易开板)"
    print(f"  封单 {snap['bid1_vol']:.0f}手 = {seal_yi:.2f}亿 = 流通盘 {seal_pct:.2f}% → {seal_level}")
    print(f"  全天 内盘 {snap['inner']:.0f} / 外盘 {snap['outer']:.0f} (外盘占比 {outer_ratio:.1f}%)")

    if yizi:
        print("  开盘即封，全天未开板（一字/封死板）")
        print("  ⚠️ 封死板的全天内外盘失真，不要用外盘占比下结论")
        print(f"  一字板看次日：封单占流通 {seal_pct:.2f}% "
              f"({'偏薄，易开板' if seal_pct < 1.5 else '较厚'})")
        return 0

    if pre_seal:
        print(f"  封板前震荡 {len(pre_seal)} 段（首封 {fmt_t(fbt_raw)} 之前，不算开板）:")
        for s in pre_seal:
            print(f"    {s['start']}→{s['end']}  {s['mins']}分钟  最低{s['low']:.2f}  相对涨停{s['drop_pct']:.2f}%")

    if not post_seal:
        print("  首次封板后未再打开（全天 0 次开板）")
        return 0

    print(f"  真开板 {len(post_seal)} 段:")
    for s in post_seal:
        print(f"    {s['start']}→{s['end']}  {s['mins']}分钟  最低{s['low']:.2f}  回落{s['drop_pct']:.2f}%")

    first = post_seal[0]
    score, notes = 0, []
    if first["start"] <= "1000":
        score += 1; notes.append(f"开板早({first['start']})→偏洗")
    elif first["start"] >= "1330":
        notes.append(f"开板晚({first['start']})→偏派发")
    else:
        score += 1; notes.append(f"开板在{first['start']}→中性偏洗")

    if first["drop_pct"] > -3:
        score += 1; notes.append(f"回落仅{first['drop_pct']:.2f}%→浅，偏洗")
    elif first["drop_pct"] < -5:
        notes.append(f"回落{first['drop_pct']:.2f}%→深，警惕派发")
    else:
        score += 1; notes.append(f"回落{first['drop_pct']:.2f}%→中性")

    if first["mins"] <= 15:
        score += 1; notes.append(f"开板仅{first['mins']}分钟→快速回封，偏洗")
    elif first["mins"] >= 30:
        notes.append(f"开板{first['mins']}分钟未回封→偏弱")
    else:
        score += 1; notes.append(f"开板{first['mins']}分钟→中性")

    if outer_ratio >= 50:
        score += 1; notes.append(f"外盘占比{outer_ratio:.1f}%→主动买占优")
    else:
        notes.append(f"外盘占比{outer_ratio:.1f}%→内盘占优，警惕砸盘")

    print(f"  分歧分 {score}/4  " + "｜".join(notes))
    print(f"  判读: " + ("偏洗筹（承接有效）" if score >= 3 else
                        "中性，需次日确认" if score == 2 else "偏派发，别接"))
    return score


if __name__ == "__main__":
    for c in (sys.argv[1:] or ["sh603089"]):
        try:
            diag(c)
        except Exception as e:
            print(f"\n=== {c} 失败: {e!r}")
