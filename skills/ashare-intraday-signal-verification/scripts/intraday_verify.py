#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日内信号验证探针 — 内外盘 / 五档厚度 / 假托单 / 做T适用性初判

用法:
    python3 intraday_verify.py sz000001 sz000002 sz159930
    python3 intraday_verify.py sh000003 --cost 12.90

输出:
    · 内盘/外盘/外盘占比
    · 买1-5 / 卖1-5 合计手数 + 买卖厚度比
    · 假托单判定（买盘厚但内盘≫外盘）
    · 做T适用性初判（单边下跌 / 逼近跌停 / 深亏 → 否决）

判据来源: skill ashare-intraday-signal-verification
"""
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def gbk(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("gbk", "ignore")


def parse_q(code, raw):
    """从腾讯批量行情里挑出指定代码那一行"""
    for line in raw.strip().split("\n"):
        if '"' not in line:
            continue
        head, _, body = line.partition('="')
        if code not in head:
            continue
        return body.rstrip('";').split("~")
    return None


def fnum(f, i, default=0.0):
    try:
        return float(f[i])
    except (IndexError, ValueError, TypeError):
        return default


def analyze(code, cost=None):
    f = parse_q(code, gbk(f"http://qt.gtimg.cn/q={code}"))
    if not f or len(f) < 40:
        print(f"\n【{code}】行情拉取失败")
        return

    name = f[1]
    px = fnum(f, 3)
    prev = fnum(f, 4)
    chg = fnum(f, 32)
    high = fnum(f, 33)
    low = fnum(f, 34)

    inner = fnum(f, 7)   # 内盘（主动卖）
    outer = fnum(f, 8)   # 外盘（主动买）
    tot = inner + outer
    outer_pct = outer / tot * 100 if tot else 0.0

    # 五档
    buy_vol = sum(fnum(f, 10 + i * 2) for i in range(5))
    sell_vol = sum(fnum(f, 20 + i * 2) for i in range(5))
    ratio_bs = buy_vol / sell_vol if sell_vol else float("inf")

    limit_down = round(prev * 0.9, 2) if prev else 0.0
    dist_ld = (px / limit_down - 1) * 100 if limit_down else 0.0

    print(f"\n{'='*72}")
    print(f"【{name} {code}】{px:.3f}（{chg:+.2f}%）  高 {high:.3f} / 低 {low:.3f}")
    if cost:
        print(f"  成本 {cost} → 盈亏 {(px/cost-1)*100:+.2f}%")
    print(f"{'='*72}")

    # ① 内外盘
    side = "🟢 主动买占优" if outer_pct > 55 else ("🔴 主动卖占优" if outer_pct < 45 else "🟡 均衡")
    print(f"① 内外盘：内盘 {inner:,.0f} / 外盘 {outer:,.0f} → 外盘占比 {outer_pct:.1f}%  {side}")

    # ② 五档厚度
    print(f"② 五档：买1-5 合计 {buy_vol:,.0f} 手 / 卖1-5 合计 {sell_vol:,.0f} 手 → 买卖比 {ratio_bs:.2f}")

    # ③ 假托单判定
    if ratio_bs > 1.5 and outer_pct < 45:
        print(f"③ 🔴🔴 假托单：买盘是卖盘的 {ratio_bs:.1f} 倍，但主动卖占 {(100-outer_pct):.1f}%")
        print(f"   → 挂单是幌子，实际在砸。立即减仓，别被买1大单骗。")
    elif ratio_bs < 0.7 and outer_pct > 55:
        print(f"③ 🟢 惜售 + 主动买（最强形态）")
    elif ratio_bs > 1.5 and outer_pct > 55:
        print(f"③ 🟢 真承接（买盘厚且主动买占优）")
    else:
        print(f"③ 🟡 盘口无明确信号，看开盘30分钟定方向")

    # ④ 做T适用性
    print(f"④ 做T初判：")
    veto = []
    if chg <= -5:
        veto.append(f"单日已跌 {chg:.1f}%（单边下跌，正T会卖在低点买在高点）")
    if dist_ld < 2:
        veto.append(f"距跌停仅 {dist_ld:.1f}%（刀口舔血）")
    if cost and (px / cost - 1) * 100 < -15:
        veto.append(f"已亏 {(px/cost-1)*100:.1f}%（摊薄杯水车薪，该减仓不该做T）")
    if buy_vol < 200:
        veto.append(f"买1-5 仅 {buy_vol:.0f} 手（卖了可能买不回）")
    if veto:
        for v in veto:
            print(f"   ❌ {v}")
        print(f"   → 结论：不建议做 T")
    else:
        print(f"   ✅ 前置条件未触发否决，但仍需确认「大盘不是单边下跌」")
        print(f"   → 若做：卖点在 9:30-10:00，卖了不追、买回更低、仓位≤底仓1/2、连错2次停手")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cost = None
    codes = []
    i = 0
    while i < len(args):
        if args[i] == "--cost" and i + 1 < len(args):
            cost = float(args[i + 1])
            i += 2
        else:
            codes.append(args[i])
            i += 1
    for c in codes:
        try:
            analyze(c, cost)
        except Exception as e:
            print(f"\n【{c}】分析失败：{e}")


if __name__ == "__main__":
    main()
