# 从零搭建 5minbtc

> 目标：在一台干净的 macOS 上，把 5minbtc 的引擎 + 6 个常驻服务跑起来。
> **验证状态**：本文依据当前**正在运行**的配置转录（2026-09-10，已核对 6 个 plist 的实际参数与进程）。
> 尚未在干净机器上实测，首次照做时请以「§5 验证清单」逐项确认。

## 1. 前置条件

| 项 | 要求 | 说明 |
|----|------|------|
| 系统 | macOS | 用 launchd 托管，Linux 需改 systemd |
| Python | 系统自带 `/usr/bin/python3` | **零第三方依赖**（`dependencies-stdlib only`）。不要用 brew/venv 的 python，plist 里写死了 `/usr/bin/python3` |
| 网络 | 能访问 `data-api.binance.vision` | `fapi.binance.com` 在本机返回 **451**（地区限制），见 §6 |
| 可选 | 币安 API key/secret | 仅预测市场下单/查价需要；纯 paper 也建议配（查盘口要签名） |

## 2. 目录布局

```
~/.claude/skills/5minbtc/          # skill 本体（引擎 + 脚本 + 文档）
├── 5minbtc-engine-v6.0.py         # 主引擎
├── 5minbtc-log.py                 # 日志/settle
├── 5minbtc-news.py                # CoinDesk RSS
├── scripts/                       # 监控/交易/采集脚本
├── references/                    # 专题文档（含本文件）
└── logs/                          # 运行时日志（见 §7）

~/bb-auto/                          # 运行时状态（不在 skill 内）
├── prediction.env                 # 密钥（600 权限）
├── ofi.json                       # OFI 采集缓存
├── prediction-ws.json             # 预测市场 WS 价缓存
├── 5minbtc-paper.json             # paper 台账
├── paper_monitor.sh               # trader 的守护壳
├── bb_paper.sh                    # bb-scalper 的守护壳
└── logs/                          # launchd stdout/stderr

~/AGI-Super-Team/                   # 共享仓库（git，分支 main）
```

## 3. 密钥与环境

```bash
mkdir -p ~/bb-auto/logs
cat > ~/bb-auto/prediction.env <<'EOF'
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx
EOF
chmod 600 ~/bb-auto/prediction.env
```

- 字段名以 skill 内 `.env.example` 为准（`scripts/*.py` 用 `load_env()` 读它）。
- **引擎本身不读环境变量**（`.env.example` 里有说明）。
- Telegram 推送不需要单独配：统一走 `scripts/telegram_push.py`，从 `~/.cc-connect/config.toml` 读 bot token + chat_id。

## 4. launchd 常驻服务（6 个）

| Label | 执行体 | 作用 |
|-------|--------|------|
| `com.daniel.ofi-feed` | `python3 .../scripts/ofi_feed.py` | 真订单流采集 → `~/bb-auto/ofi.json` |
| `com.daniel.prediction-ws-feed` | `python3 .../scripts/prediction_ws_feed.py` | 预测市场 WS 实时价（<200ms） |
| `com.daniel.5minbtc-realtime` | `python3 .../scripts/5minbtc_realtime.py --conf 70 --refresh 5 --active-hours 20,21,22,23 --push` | 5s 刷新，推预测快照 + EV 下单 |
| `com.daniel.5minbtc-watch` | `python3 .../scripts/5minbtc_watch.py --mute` | 事件驱动推送 + 预测记录/结算 |
| `com.daniel.5minbtc-paper` | `/bin/bash ~/bb-auto/paper_monitor.sh` | 跑 `5minbtc_trader.py --paper-monitor` |
| `com.daniel.bb-paper` | `/bin/bash ~/bb-auto/bb_paper.sh` | bb-scalper 模拟盘（另一个 skill） |

### plist 模板

`ThrottleInterval` 防止崩溃循环打爆 CPU；`KeepAlive` 保证崩溃自启。把 `__LABEL__` / `__ARGS__` 换掉即可：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>            <string>__LABEL__</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>__SCRIPT__</string>
        <!-- 其余参数依次一行一个 <string> -->
    </array>
    <key>RunAtLoad</key>        <true/>
    <key>KeepAlive</key>        <true/>
    <key>ProcessType</key>      <string>Background</string>
    <key>ThrottleInterval</key> <integer>5</integer>
    <key>StandardOutPath</key>  <string>/Users/<你>/bb-auto/logs/launchd-__TAG__.out.log</string>
    <key>StandardErrorPath</key><string>/Users/<你>/bb-auto/logs/launchd-__TAG__.err.log</string>
</dict>
</plist>
```

### 加载

```bash
cp com.daniel.xxx.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.daniel.xxx.plist
```

### 管理命令

```bash
launchctl list | grep daniel                                  # 总览
launchctl kickstart -k gui/$(id -u)/com.daniel.5minbtc-watch  # 重启（改代码后用 -k）
launchctl bootout gui/$(id -u)/com.daniel.5minbtc-watch       # 停止
```

> ⚠️ **改了引擎文件名必须重启**：`ENGINE` 是模块级常量，进程不会自动感知新路径；
> 且 `run_engine()` 是 `except: return None` **静默吞异常** —— 路径错了不会报错，只会安静地不下单。
> 判断是否在跑：`ps aux | grep 5minbtc-engine` 应能看到子进程反复出现。

## 5. 验证清单

```bash
S=~/.claude/skills/5minbtc

# 1. 引擎能跑出 JSON，且 version 正确
$S/5minbtc-engine-v6.0.py | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['version'], d['prediction']['bias'])"
# 期望: 6.0.0 <bull|bear>

# 2. 方向来自 OFI（bias 应与 ofi.direction 一致）
$S/5minbtc-engine-v6.0.py | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['prediction']['bias'], d['ofi']['direction'], d['ofi']['ofi_n'])"

# 3. 6 个服务都在
launchctl list | grep daniel

# 4. 无引擎路径错误
grep -il "No such file\|FileNotFound" ~/bb-auto/logs/launchd-*.log || echo "✅ 无路径错误"

# 5. OFI 缓存新鲜（引擎要求 <30s，否则 WS 分量降级）
python3 -c "import json,time; d=json.load(open('$HOME/bb-auto/ofi.json')); print('age(s)=', round(time.time()-d['ts']/1000,1))"
```

## 6. 网络/地区修复（geo）

- `fapi.binance.com` REST 在本机 **451**（地区限制）。已改用：
  - REST 行情 → **`data-api.binance.vision`**（引擎内默认）
  - WS → `fstream.binance.com`
- 详见 [binance-api-geo.md](binance-api-geo.md) 与 [binance-endpoint-flapping.md](binance-endpoint-flapping.md)。
- ⚠️ `fstream` 的 `kline` / `aggTrade` 流在本网络**不推送**，只有 `trade` / `bookTicker` 流可用 —— 这正是 `ofi_feed.py` 用 `trade+bookTicker` 组合的原因（`@trade` 自带原生 `m` 主动买卖标记）。
- 高延迟网络下的 SSL 超时处理见 [high-latency-network-handling.md](high-latency-network-handling.md)。

## 7. 日志轮转

`logs/` 采用「当月 live + 历史按月压缩」；压缩归档入库，live 不入库（见 [archive.md](archive.md#日志归档)）。
轮转脚本（幂等，可重复跑）：

```bash
cd ~/.claude/skills/5minbtc && python3 - <<'PY'
import gzip, json, os, tempfile
from collections import defaultdict
from pathlib import Path

LIVE, ARCH = Path("logs/5minbtc-log.jsonl"), Path("logs/archive")
ARCH.mkdir(parents=True, exist_ok=True)

by_month, bad = defaultdict(list), 0
for line in LIVE.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    try:
        by_month[json.loads(line).get("ts", "")[:7]].append(line)
    except Exception:
        bad += 1

CURRENT = max(by_month)
for month, lines in sorted(by_month.items()):
    if month == CURRENT:
        continue
    out = ARCH / f"5minbtc-log.{month}.jsonl.gz"
    with gzip.open(out, "wt", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"归档 {month}: {len(lines)} 行 → {out}")

keep = by_month[CURRENT]
tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir="logs")
tmp.write("\n".join(keep) + "\n"); tmp.close()
os.replace(tmp.name, LIVE)          # 原子替换；写日志的是短命子进程(O_APPEND)，不会踩坏
print(f"live 保留 {CURRENT}: {len(keep)} 行 | 解析失败 {bad} 行")
PY
```

轮转后**校验行数守恒**（归档行数 + live 行数 == 轮转前总行数）再提交。

## 8. 常见故障

| 现象 | 原因 | 处理 |
|------|------|------|
| 引擎跑但一直不下单，日志无报错 | `ENGINE` 路径失效（静默吞异常） | `ps aux \| grep 5minbtc-engine` 看子进程是否在起 |
| 改了引擎但不生效 | 守护进程持旧常量 | `launchctl kickstart -k` 重启 |
| 预测市场价拿不到 | WS 未连上或签名失效 | 查 `launchd-ws-feed.err.log`；确认 key/secret |
| 引擎卡 30s+ | Binance SSL 超时 | 见 [high-latency-network-handling.md](high-latency-network-handling.md) |
| `OFI feed_fresh=false` | `ofi.json` 超过 30s 未更新 | 查 `com.daniel.ofi-feed` 是否存活 |
| cron/launchd 报 451 | geo 限制 | 改用 `data-api.binance.vision` |

## 9. 同步到共享仓库

见 [sync-procedure.md](sync-procedure.md)（含路径映射与 `-c` 校验说明）。
