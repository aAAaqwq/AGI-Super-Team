#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A股技术指标标准实现：MA / RSI / MACD + 状态判断辅助。
用法：from indicators import calc_indicators; calc_indicators(closes)
"""
from typing import List, Optional


def ma(data: List[float], n: int) -> List[float]:
    out = []
    s = 0.0
    for i, v in enumerate(data):
        s += v
        if i >= n:
            s -= data[i - n]
        out.append(s / min(n, i + 1))
    return out


def rsi(data: List[float], n: int = 14) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(data)
    if len(data) <= n:
        return out
    gains = losses = 0.0
    for i in range(1, n + 1):
        ch = data[i] - data[i - 1]
        gains += max(ch, 0.0)
        losses += max(-ch, 0.0)
    ag, al = gains / n, losses / n
    out[n] = 100 - 100 / (1 + (ag / al if al else 999))
    for i in range(n + 1, len(data)):
        ch = data[i] - data[i - 1]
        ag = (ag * (n - 1) + max(ch, 0.0)) / n
        al = (al * (n - 1) + max(-ch, 0.0)) / n
        out[i] = 100 - 100 / (1 + (ag / al if al else 999))
    return out


def _ema(data: List[float], n: int) -> List[float]:
    out = [data[0]]
    m = 2 / (n + 1)
    for v in data[1:]:
        out.append(v * m + out[-1] * (1 - m))
    return out


def macd(data: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
    ef, es = _ema(data, fast), _ema(data, slow)
    dif = [a - b for a, b in zip(ef, es)]
    dea = _ema(dif, signal)
    hist = [(a - b) * 2 for a, b in zip(dif, dea)]
    return dif, dea, hist


def calc_indicators(closes: List[float]):
    """返回最近一根K线的指标快照 + 全序列，供报告使用。"""
    ma5, ma10, ma20, ma60 = ma(closes, 5), ma(closes, 10), ma(closes, 20), ma(closes, 60)
    r = rsi(closes)
    dif, dea, hist = macd(closes)
    i = len(closes) - 1
    return {
        "close": closes[i],
        "ma5": ma5[i], "ma10": ma10[i], "ma20": ma20[i], "ma60": ma60[i],
        "rsi14": r[i],
        "dif": dif[i], "dea": dea[i], "hist": hist[i],
        "ma_bull": ma5[i] > ma10[i] > ma20[i],
        "close_above_ma5": closes[i] > ma5[i],
        "ma20_above_ma60": ma20[i] > ma60[i],
        "rsi_overbought": (r[i] or 0) > 70,
        "chg_5d": closes[i] / closes[-5] - 1,
        "chg_10d": closes[i] / closes[-10] - 1,
        "chg_20d": closes[i] / closes[-20] - 1,
        "chg_60d": closes[i] / closes[-60] - 1 if len(closes) >= 60 else None,
    }


if __name__ == "__main__":
    # 自测
    import random
    random.seed(1)
    sample = [10 + i * 0.1 + random.uniform(-0.5, 0.5) for i in range(80)]
    snap = calc_indicators(sample)
    for k, v in snap.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")
