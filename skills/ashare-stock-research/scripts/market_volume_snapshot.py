#!/usr/bin/env python3
"""大盘/科技板块量能快照：竞价额、开盘30分钟额、全天额、占两市比重、竞价环比。

用法:
    python3 market_volume_snapshot.py                 # 默认看大盘+科技四条线
    python3 market_volume_snapshot.py sh000001 sz399006
数据源: 腾讯 web.ifzq.gtimg.cn/appstock/app/day/query  (近5个交易日逐分钟)
口径见 references/market-volume-analysis.md
"""
import sys, json, time, urllib.request

UA = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gu.qq.com/'}
DEFAULT = ['sh000001', 'sz399106', 'sz399811', 'sh000685', 'sh000998', 'sz399006']
NAMES = {'sh000001': '上证指数', 'sz399106': '深证综指', 'sz399811': 'CSSW电子',
         'sh000685': '科创芯片', 'sh000998': '中证TMT', 'sz399006': '创业板指',
         'sh000688': '科创50', 'sz399001': '深证成指'}


def fetch(url, enc='utf-8'):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=20).read().decode(enc, errors='ignore')


def day5(code):
    """近5个交易日逐分钟，返回最新在前的列表；失败返回 None"""
    for _ in range(3):
        try:
            j = json.loads(fetch(f"https://web.ifzq.gtimg.cn/appstock/app/day/query?code={code}"))
            return j['data'][code]['data']
        except Exception:
            time.sleep(1.5)
    return None


def seg(rows):
    """rows 是 ["HHMM price cum_vol cum_amt", ...]，返回亿元口径的竞价/前30min/全天"""
    sp = [r.split() for r in rows]

    def cum(h):
        for p in sp:
            if p[0] == h:
                return float(p[3])
        return None

    e0 = float(sp[0][3])
    total = float(sp[-1][3])
    m1000 = cum('1000')
    return {'auc': e0 / 1e8, 'open30': (m1000 - e0) / 1e8 if m1000 else float('nan'),
            'total': total / 1e8}


def main(codes):
    store = {}
    for c in codes:
        d = day5(c)
        if d:
            store[c] = {x['date']: x['data'] for x in d}   # {date: rows}
        else:
            print(f"!! {c} 取数失败", file=sys.stderr)
        time.sleep(0.5)
    if not store:
        return
    dates = sorted({d for v in store.values() for d in v})
    print(f"数据区间: {dates[0]} ~ {dates[-1]}（腾讯近5个交易日逐分钟）\n")

    # 表1 两市总成交额与日内节奏
    plain = [c for c in ('sh000001', 'sz399106') if c in store]
    if len(plain) == 2:
        print("【表1】两市总成交额节奏（亿元）")
        print(f"{'日期':<10}{'竞价':>8}{'9:30-10:00':>12}{'全天':>10}{'早盘占比':>10}")
        for d in dates:
            s = seg(store['sh000001'][d]); z = seg(store['sz399106'][d])
            tot = s['total'] + z['total']; o30 = s['open30'] + z['open30']
            print(f"{d:<10}{s['auc']+z['auc']:>8.0f}{o30:>12.0f}{tot:>10.0f}{o30/tot*100:>9.1f}%")

    # 表2 竞价额/前30min 环比
    print("\n【表2】竞价额 与 开盘30分钟额 环比（时间正序，倒序数据已反转）")
    for c in codes:
        if c not in store:
            continue
        print(f"--- {NAMES.get(c, c)} {c} ---")
        prev = None
        for d in dates:
            if d not in store[c]:
                continue
            v = seg(store[c][d])
            sa = f"{(v['auc']/prev[0]-1)*100:+.1f}%" if prev else "--"
            s3 = f"{(v['open30']/prev[1]-1)*100:+.1f}%" if prev else "--"
            print(f"  {d}  竞价{v['auc']:>7.1f}亿 ({sa:>7})  前30min{v['open30']:>8.1f}亿 ({s3:>7})  全天{v['total']:>8.1f}亿")
            prev = (v['auc'], v['open30'])
    print("\n判读阈值: 竞价/昨全天 0.5~1.0% 正常, >+30%环比=隔夜有增量信息;")
    print("          前30min/昨全天 >40% 超高换手, 竞价放量+前30min缩量 = 假放量/诱多")


if __name__ == '__main__':
    main(sys.argv[1:] or DEFAULT)
