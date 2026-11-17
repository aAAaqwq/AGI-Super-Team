# 技术指标纯 Python 实现 + K线图画法

标准实现，直接内嵌到分析脚本。K线数据来自腾讯 fqkline（`[[date, open, close, high, low, vol],...]`，**close 是索引 2**）。

## MA / RSI / MACD

```python
def ma(data, n):
    out = []
    s = 0
    for i, v in enumerate(data):
        s += v
        if i >= n: s -= data[i-n]
        out.append(s / min(n, i+1))
    return out

def rsi(data, n=14):
    out = [None]*len(data)
    if len(data) <= n: return out
    gains = losses = 0
    for i in range(1, n+1):
        ch = data[i]-data[i-1]
        gains += max(ch,0); losses += max(-ch,0)
    ag, al = gains/n, losses/n
    out[n] = 100 - 100/(1+(ag/al if al else 999))
    for i in range(n+1, len(data)):
        ch = data[i]-data[i-1]
        ag = (ag*(n-1)+max(ch,0))/n
        al = (al*(n-1)+max(-ch,0))/n
        out[i] = 100 - 100/(1+(ag/al if al else 999))
    return out

def ema(data, n):
    out = [data[0]]
    m = 2/(n+1)
    for v in data[1:]:
        out.append(v*m + out[-1]*(1-m))
    return out

# MACD: fast=12, slow=26, signal=9
ef, es = ema(closes,12), ema(closes,26)
dif = [a-b for a,b in zip(ef,es)]
dea = ema(dif,9)
hist = [(a-b)*2 for a,b in zip(dif,dea)]
```

## 输出判断模板

```python
i = len(closes)-1
print(f"收:{closes[i]:.2f} MA5:{ma5[i]:.2f} MA10:{ma10[i]:.2f} MA20:{ma20[i]:.2f} MA60:{ma60[i]:.2f}")
print(f"RSI14:{rsi[i]:.1f} | MACD DIF:{dif[i]:.3f} DEA:{dea[i]:.3f} HIST:{hist[i]:.3f}")
print(f"5日:{(closes[i]/closes[i-5]-1)*100:+.1f}% 10日:{(closes[i]/closes[i-10]-1)*100:+.1f}% 20日:{(closes[i]/closes[i-20]-1)*100:+.1f}%")
# 均线多头: ma5>ma10>ma20; 收>MA5; MA20>MA60; RSI超买: rsi>70
# 涨停价=round(close*1.1,2) 跌停价=round(close*0.9,2)  — 注意实际按交易所规则四舍五入到分
```

## matplotlib K线图（lazy-packages 环境）

matplotlib 不在系统 python，需：
```python
import sys
sys.path.insert(0, '$PY_EXTRA_PACKAGES')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
```

画图要点（近 60 日三面板：K线+MA / 成交量 / MACD）：
- **x 轴用 datetime 对象**：`x = [datetime.strptime(dt, "%Y-%m-%d") for dt in dates]`
- 画 K 线实体用 `plt.Rectangle((mdates.date2num(x[i])-0.25, body_b), 0.5, body_h, ...)` —— **必须 mdates.date2num 转数值**，不能 datetime 减 float
- 红涨绿跌（A股习惯）：`color = '#e33b3b' if close>=open else '#2e9e4f'`
- 影线：`ax1.plot([x[i],x[i]],[lows[i],highs[i]], color=color, linewidth=1)`
- 三面板：`fig, (ax1,ax2,ax3) = plt.subplots(3,1, sharex=True, gridspec_kw={'height_ratios':[3,1,1]})`
- 保存：`plt.savefig('$AST_DATA_DIR/images/<name>_kline.png', bbox_inches='tight')`，回复末尾加 `MEDIA:$AST_DATA_DIR/images/<name>_kline.png`

常见报错 `TypeError: unsupported operand type(s) for -: 'datetime.datetime' and 'float'` = 忘了 mdates.date2num。
