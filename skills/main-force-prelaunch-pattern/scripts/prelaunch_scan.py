#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主力拉升前五步曲 - 地量伏击扫描器

用法:
  python3 prelaunch_scan.py                    # 扫描候选（默认扫龙擎主力池）
  python3 prelaunch_scan.py --codes 002403,002368   # 扫指定股票
  python3 prelaunch_scan.py --watch            # 检查观察池状态（观察期/确认启动）
  python3 prelaunch_scan.py --add 002403       # 手动加入观察池
  python3 prelaunch_scan.py --remove 002403    # 从观察池移除
  python3 prelaunch_scan.py --pool             # 只看观察池列表

铁律: 扫描只是"发现"，买入必须等"确认启动"（阶段3）。
"""
import os
import sys
import json
import time
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
WATCH_FILE = os.path.join(HERE, ".prelaunch_watch.json")

# 可调阈值（与 SKILL.md 一致）
TH_VOLUME_MAX = 0.70      # 地量：今日量 / 20日均量 上限
TH_MA30_RANGE = 5.0       # 距 MA30 上下限(%)
TH_CHG_RANGE = 3.0        # 起涨日涨跌幅上下限(%)
TH_TEST_VOLUME = 1.30     # 前期试盘放量门槛
TH_HEAVY_VOLUME = 3.0     # 天量门槛（近10日排除）
TH_OBSERVE_MAX_DAYS = 8   # 观察期上限（交易日）


def bjnow():
    return datetime.now(BJ)


def http(url, timeout=20, enc="utf-8"):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode(enc, "ignore")


def load_watch():
    if os.path.exists(WATCH_FILE):
        try:
            return json.load(open(WATCH_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"items": {}}


def save_watch(w):
    json.dump(w, open(WATCH_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def tc(code):
    """补全市场前缀。已是 sh/sz 开头的直接返回，避免 szsz399006。"""
    c = code.split(".")[0]
    if c.startswith(("sh", "sz", "bj")):
        return c
    return ("sh" if c.startswith("6") else "sz") + c


def kline(code, n=90):
    """K线：东财为主源，新浪为备源（腾讯 ifzq 2026-10 起返回 501，已弃用）

    返回 [{"d","o","c","h","l","v"}]，v 单位 = 手
    """
    sym = tc(code)
    c6 = code.split(".")[0]
    secid = ("1." if c6.startswith("6") else "0.") + c6

    # 主源：东财 push2his（格式 日期,开,收,高,低,量(手),额）
    try:
        url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
               f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
               f"&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20500101&lmt={n}")
        d = json.loads(http(url))
        kl = (d.get("data") or {}).get("klines") or []
        if kl:
            out = []
            for s in kl:
                p = s.split(",")
                out.append({"d": p[0], "o": float(p[1]), "c": float(p[2]),
                            "h": float(p[3]), "l": float(p[4]), "v": float(p[5])})
            return out
    except Exception:
        pass

    # 备源：新浪（volume 单位是股，除以 100 转手）
    try:
        url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
               f"CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={n}")
        d = json.loads(http(url))
        if d:
            return [{"d": x["day"], "o": float(x["open"]), "c": float(x["close"]),
                     "h": float(x["high"]), "l": float(x["low"]),
                     "v": float(x["volume"]) / 100} for x in d]
    except Exception:
        pass

    return None


def quote(codes):
    if not codes:
        return {}
    out = {}
    for i in range(0, len(codes), 40):
        batch = codes[i:i + 40]
        try:
            raw = http("http://qt.gtimg.cn/q=" + ",".join(batch), enc="gbk")
        except Exception:
            continue
        for line in raw.strip().split("\n"):
            if '"' not in line:
                continue
            f = line.split('"')[1].split("~")
            if len(f) < 46:
                continue
            try:
                out[f[2]] = {
                    "name": f[1], "px": float(f[3]), "chg": float(f[32]),
                    "hs": f[38], "lb": f[49] if len(f) > 49 else "0",
                    "ltsz": float(f[44]) if f[44] else 0, "pe": f[39],
                }
            except Exception:
                pass
        time.sleep(0.15)
    return out


def analyze(code, name=None):
    """返回形态分析结果 dict，不合格返回 None + 原因"""
    rows = kline(code)
    if not rows or len(rows) < 40:
        return None, "K线不足"
    c = [r["c"] for r in rows]
    v = [r["v"] for r in rows]
    o = [r["o"] for r in rows]
    h = [r["h"] for r in rows]
    l = [r["l"] for r in rows]

    ma = lambda n: sum(c[-n:]) / n
    v20 = sum(v[-21:-1]) / 20
    if v20 <= 0:
        return None, "量能异常"

    vr = v[-1] / v20
    chg = (c[-1] / c[-2] - 1) * 100
    dist30 = (c[-1] / ma(30) - 1) * 100

    last_vol = v[-1] / 10000
    body = (c[-1] - o[-1]) / c[-2] * 100
    tot = h[-1] - l[-1]
    lower_shadow = (min(c[-1], o[-1]) - l[-1]) / tot if tot > 0 else 0

    # 检查项
    checks = {
        "地量": vr <= TH_VOLUME_MAX,
        "贴近MA30": abs(dist30) <= TH_MA30_RANGE,
        "当天平淡": abs(chg) <= TH_CHG_RANGE,
        "前期有试盘": any(v[i] / v20 > TH_TEST_VOLUME for i in range(max(0, len(v) - 25), len(v))),
        "近10日无天量": not any(v[i] / v20 > TH_HEAVY_VOLUME for i in range(max(0, len(v) - 10), len(v))),
    }
    # 加分项
    bonus = {
        "长下影": lower_shadow > 0.45,
        "近2日有最后一跌": any((c[i] / c[i - 1] - 1) * 100 < -3 and v[i] / v20 < 1.2 for i in range(len(c) - 2, len(c))),
        "MA30走平向上": ma(30) >= sum(c[-40:-10]) / 30 * 0.98,
        "近期未涨停": not any((c[i] / c[i - 1] - 1) * 100 >= 9.5 for i in range(max(0, len(c) - 20), len(c))),
    }

    passed = all(checks.values()) and bonus["近期未涨停"]

    reason = []
    if not checks["地量"]:
        reason.append(f"量{vr:.2f}x")
    if not checks["贴近MA30"]:
        reason.append(f"距MA30{dist30:+.1f}%")
    if not checks["当天平淡"]:
        reason.append(f"涨跌{chg:+.1f}%")
    if not checks["前期有试盘"]:
        reason.append("无试盘")
    if not checks["近10日无天量"]:
        reason.append("有死量")
    if not bonus["近期未涨停"]:
        reason.append("已涨停过(非起涨前)")

    return {
        "code": code, "name": name or code, "px": c[-1], "chg": chg,
        "vr": vr, "dist30": dist30, "body": body, "lower_shadow": lower_shadow,
        "ma5": ma(5), "ma10": ma(10), "ma20": ma(20), "ma30": ma(30), "ma60": ma(60),
        "v20": v20, "last_vol_wan": last_vol,
        "checks": checks, "bonus": bonus, "passed": passed, "reason": " / ".join(reason),
        "hi250": max(h[-250:]) if len(h) >= 250 else max(h),
        "lo250": min(l[-250:]) if len(l) >= 250 else min(l),
        "date": rows[-1]["d"],
    }, None


def market_ok():
    """大盘环境检查：创业板近3日累计跌幅"""
    try:
        rows = kline("sz399006", 10)
        if not rows or len(rows) < 4:
            return True, "数据不足，默认通过"
        c = [r["c"] for r in rows]
        cum = (c[-1] / c[-4] - 1) * 100
        if cum < -5:
            return False, f"创业板近3日 {cum:+.1f}% → 暂停扫描（急跌中地量=无人问津）"
        return True, f"创业板近3日 {cum:+.1f}% → 可扫描"
    except Exception as e:
        return True, f"检查失败({e})，默认通过"


def get_pool_codes():
    """从龙擎主力池取股票代码（凭证从环境变量读，不硬编码）"""
    username = os.environ.get("LONGQIN_USERNAME", "admin")
    password = os.environ.get("LONGQIN_PASSWORD", "")
    if not password:
        print("  ⚠️ 未设置 LONGQIN_PASSWORD 环境变量，跳过主力池拉取（可用 --codes 指定）")
        return []
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        base = "https://longqin.hanxai.cn"
        req = urllib.request.Request(
            base + "/api/auth/login",
            data=json.dumps({"username": username, "password": password}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        tok = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())["access_token"]
        req2 = urllib.request.Request(base + "/api/v7/main-pool",
                                      headers={"Authorization": "Bearer " + tok, "User-Agent": "Mozilla/5.0"})
        d = json.loads(urllib.request.urlopen(req2, timeout=30, context=ctx).read())
        return [x["code"] for x in d.get("items", [])]
    except Exception as e:
        print(f"  ⚠️ 主力池拉取失败: {e}")
        return []


def cmd_scan(codes=None):
    now = bjnow()
    print(f"⏰ {now.strftime('%Y-%m-%d %H:%M')} 主力拉升前扫描")
    print("=" * 78)

    ok, msg = market_ok()
    print(f"环境检查: {msg}")
    if not ok:
        print("  ⛔ 结论: 今天不适用本框架（大盘急跌，地量≠吸筹）")
        print("=" * 78)
        return

    if not codes:
        print("正在拉取龙擎主力池...")
        codes = get_pool_codes()
        if not codes:
            print("  ⛔ 无股票池，请用 --codes 指定")
            return

    print(f"扫描 {len(codes)} 只...")
    q = quote([tc(c) for c in codes])

    passed, failed = [], []
    for code in codes:
        c6 = code.split(".")[0]
        nm = (q.get(c6) or {}).get("name")
        r, err = analyze(code, nm)
        if not r:
            continue
        if r["passed"]:
            passed.append(r)
        else:
            failed.append(r)
        time.sleep(0.06)

    print(f"\n✅ 符合五条必要条件: {len(passed)} 只")
    if passed:
        print(f"{'代码':<8}{'名称':<10}{'现价':>8}{'今日%':>7}{'量/20均':>8}{'距MA30':>9}{'MA30':>8}{'加分项':<20}")
        for r in sorted(passed, key=lambda x: x["vr"]):
            b = "/".join(k for k, v in r["bonus"].items() if v)
            print(f"{r['code'].split('.')[0]:<8}{r['name']:<10}{r['px']:>8.2f}{r['chg']:>+7.2f}"
                  f"{r['vr']:>8.2f}{r['dist30']:>+8.2f}%{r['ma30']:>8.2f}  {b}")
        print("\n→ 加入观察池: python3 prelaunch_scan.py --add <代码>")
        print("→ 铁律: 现在不能买！等「确认启动」(阶段3)出现才买")
    else:
        print("  （无）")

    print(f"\n❌ 不合格: {len(failed)} 只（前8只）")
    for r in sorted(failed, key=lambda x: x["vr"])[:8]:
        print(f"  {r['code'].split('.')[0]:<8}{r['name']:<10} {r['reason']}")
    print("=" * 78)


def cmd_add(codes):
    w = load_watch()
    q = quote([tc(c) for c in codes])
    for code in codes:
        c6 = code.split(".")[0]
        nm = (q.get(c6) or {}).get("name")
        r, err = analyze(code, nm)
        if not r:
            print(f"✗ {code}: {err or '分析失败'}")
            continue
        if not r["passed"]:
            print(f"⚠️ {c6} {r['name']} 不符合条件（{r['reason']}），仍强制加入")
        w["items"][c6] = {
            "name": r["name"], "added": bjnow().strftime("%Y-%m-%d"),
            "added_px": r["px"], "added_vr": round(r["vr"], 2),
            "ma30_at_add": round(r["ma30"], 2), "low_since": r["px"],
            "days": 0, "note": r["reason"] or "符合五条",
        }
        print(f"✅ {c6} {r['name']} 已加入观察池（起涨参考价 {r['px']:.2f}，MA30 {r['ma30']:.2f}）")
    save_watch(w)
    print(f"\n观察池共 {len(w['items'])} 只")
    print("→ 每个交易日收盘后跑 --watch 检查")


def cmd_remove(codes):
    w = load_watch()
    for c6 in codes:
        c6 = c6.split(".")[0]
        if c6 in w["items"]:
            del w["items"][c6]
            print(f"✅ 已移除 {c6}")
        else:
            print(f"✗ {c6} 不在观察池")
    save_watch(w)


def cmd_pool():
    w = load_watch()
    items = w.get("items", {})
    if not items:
        print("观察池为空")
        return
    print(f"观察池 {len(items)} 只：")
    print(f"{'代码':<8}{'名称':<10}{'加入日':<12}{'加入价':>8}{'观察天数':>8}{'备注'}")
    for c6, v in items.items():
        print(f"{c6:<8}{v.get('name',''):<10}{v.get('added',''):<12}{v.get('added_px',0):>8.2f}{v.get('days',0):>8}  {v.get('note','')}")


def cmd_watch():
    """检查观察池：观察期跟踪 + 确认启动提醒"""
    w = load_watch()
    items = w.get("items", {})
    if not items:
        print("观察池为空，先用 --add 加入候选")
        return

    now = bjnow()
    print(f"⏰ {now.strftime('%Y-%m-%d %H:%M')} 观察池检查（{len(items)} 只）")
    print("=" * 78)

    q = quote([tc(c) for c in items.keys()])
    triggers, kills, keep = [], [], []

    for c6, meta in list(items.items()):
        code = ("sh" if c6.startswith("6") else "sz") + c6
        cur = q.get(c6) or q.get(code) or {}
        if not meta.get("name") and cur.get("name"):
            meta["name"] = cur["name"]
        rows = kline(code)
        if not rows or len(rows) < 25:
            keep.append((c6, meta, "K线不足"))
            continue

        c = [r["c"] for r in rows]
        v = [r["v"] for r in rows]
        v20 = sum(v[-21:-1]) / 20
        vr = v[-1] / v20 if v20 else 0
        chg = (c[-1] / c[-2] - 1) * 100
        px = cur.get("px", c[-1])

        # 更新观察期数据
        meta["days"] = meta.get("days", 0) + 1
        meta["low_since"] = min(meta.get("low_since", px), px)

        add_px = meta.get("added_px", px)
        new_high_5 = max(c[-6:-1])

        # ===== 阶段3：确认启动判定 =====
        sig = None
        if chg >= 9.5 and vr >= 1.5:
            sig = "B 涨停启动"
        elif 3 <= chg <= 7 and 1.3 <= vr <= 2.5 and c[-1] > new_high_5:
            sig = "A 放量小阳突破5日新高"
        elif chg > 0 and vr >= 1.5 and (min(c[-1], rows[-1]["o"]) - rows[-1]["l"]) / max(0.001, rows[-1]["h"] - rows[-1]["l"]) > 0.4:
            sig = "C 放量长下影反包"
        elif all(1 <= (c[i] / c[i - 1] - 1) * 100 <= 3 for i in range(len(c) - 2, len(c))) and 0.9 <= vr <= 1.5:
            sig = "D 连续两日小阳"

        # ===== 淘汰判定 =====
        if vr > 1.5 and chg < -5:
            kills.append((c6, meta, f"放量下跌 {chg:+.1f}% / {vr:.1f}x → 主力出货"))
        elif px < meta.get("low_since", px) * 0.97:
            kills.append((c6, meta, f"跌破观察期低点 -3% → 失效"))
        elif meta["days"] > TH_OBSERVE_MAX_DAYS:
            kills.append((c6, meta, f"观察 {meta['days']} 天仍未启动 → 剔除"))
        elif sig:
            triggers.append((c6, meta, sig, px, chg, vr, add_px))
        else:
            keep.append((c6, meta, f"观察中 量{vr:.2f}x 涨{chg:+.1f}% 距加入价{(px / add_px - 1) * 100:+.1f}%"))

    if triggers:
        print("\n🚨 确认启动（可买入）")
        for c6, meta, sig, px, chg, vr, add_px in triggers:
            print(f"  {c6} {meta.get('name','')}  {px:.2f}（{chg:+.2f}%/量{vr:.1f}x）")
            print(f"    信号: {sig}")
            print(f"    加入价 {add_px:.2f} → 现价 {px:.2f}（{(px / add_px - 1) * 100:+.1f}%）")
            print(f"    ⚡ 建议: 仓位≤10% | 止损 {min(px * 0.95, rows[-1]['o'] * 0.99):.2f}")

    if kills:
        print("\n❌ 剔除")
        for c6, meta, why in kills:
            print(f"  {c6} {meta.get('name','')}: {why}")
            del items[c6]

    if keep:
        print("\n👀 观察中（不能买）")
        for c6, meta, why in keep:
            print(f"  {c6} {meta.get('name',''):<10} 第{meta.get('days',0)}天  {why}")

    save_watch(w)
    print("=" * 78)


def main():
    args = sys.argv[1:]
    if not args:
        cmd_scan()
    elif args[0] == "--codes" and len(args) > 1:
        cmd_scan(args[1].split(","))
    elif args[0] == "--add" and len(args) > 1:
        cmd_add(args[1].split(","))
    elif args[0] == "--remove" and len(args) > 1:
        cmd_remove(args[1].split(","))
    elif args[0] == "--pool":
        cmd_pool()
    elif args[0] == "--watch":
        cmd_watch()
    elif args[0] in ("-h", "--help"):
        print(__doc__)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
