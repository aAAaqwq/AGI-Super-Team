# 系统级定时任务设置教程

> **给 agent 的操作手册**：如何在 macOS（launchd）/ cc-connect / hermes 上建立本 skill 的定时任务。
> 本文覆盖 **2 个任务**（见 §1）与 **3 种实现路线**（见 §2），以及全部踩坑点（§5）。
>
> 环境实测（2026-09-10）：本机 `uid=503`，系统时区 **Asia/Shanghai (CST +0800)**，
> 与引擎内部 `CST = timezone(timedelta(hours=8))` **一致** → **所有 cron 表达式直接用本地时间写，不需要换算**。
> 本机 `~/Library/LaunchAgents/` 现有 6 个 job **全是常驻型（KeepAlive）**，定时型无先例。

---

## 0. 先分清：常驻型 vs 定时型（**最容易搞错的地方**）

| | **常驻型**（现有 6 个） | **定时型**（本文要建的） |
|---|---|---|
| 用途 | 7×24 持续跑（采集/监控/交易） | 到点跑一次就退出 |
| 关键键 | `KeepAlive=true` + `RunAtLoad=true` | **`StartCalendarInterval`，且不要配 `KeepAlive`** |
| 例子 | `ofi-feed`、`5minbtc-realtime`、`5minbtc-watch` | 每日战绩推送 |
| 配错的后果 | — | 配了 `KeepAlive` → **任务一退出就被立刻重启，变成疯狂循环** |

> ⚠️ **定时任务配 `KeepAlive` 是头号事故**。它意味着"只要进程不在了就拉起来"，
> 而定时任务的正常行为恰恰是"跑完退出" —— 两者语义直接冲突。
> 定时型只需要 `StartCalendarInterval`（可加 `RunAtLoad=false`）。

---

## 1. 这 2 个任务是什么

### 任务 A：每 5 分钟「预测 + 推送」

| 项 | 值 |
|---|---|
| hermes 机上的 job | `d8058223a1e0`「5minbtc v5.7 半K线策略」 |
| cron 表达式 | `2,7,12,17,22,27,32,37,42,47,52,57 20-22 * * *`（仅 20–22 点，每小时 12 次） |
| 干什么 | 跑完整 LLM 工作流（引擎 + 新闻 + 3 组 web_search）→ 按 `output-template.md` 出报告 → 推送 |

> ⚠️ **在 Mac 上，这个任务大概率不需要建**。因为常驻的 `com.daniel.5minbtc-realtime`
> 已经**每 5 秒**跑一次引擎并推预测快照，`--active-hours 20,21,22,23` 的时段过滤也已内建。
> **两者的区别是**：realtime 的推送是**纯规则型**（不经过 LLM，直接格式化引擎输出）；
> 定时任务 A 是**LLM 工作流型**（会调 web_search + 生成分析文字）。
> **先问清楚要哪一种，再动手** —— 只是要数据/快照的话，别建，会重复推送。

### 任务 B：每日「复盘 / 战绩」推送

| 项 | 值 |
|---|---|
| hermes 机上的 job | `9b07cd139f70`「5minbtc 每日复盘 23:15」 |
| cron 表达式 | `15 23 * * *` |
| 干什么 | 推送当日战绩统计（或 LLM 复盘） |

> ⚠️ **这个任务在 Mac 上"已经有了"，只是藏在一个常驻进程里**：
> `com.daniel.5minbtc-watch` 在主循环里检测**日期切换**，然后 `subprocess` 调
> `5minbtc_day_stats.py --date <昨天> --push`（`5minbtc_watch.py` 约 L356）。
>
> **两件必须知道的事**：
> 1. **`--mute` 不会静音每日推送** —— 它是 subprocess 直调，不走 watch 的 `push()` 包装器。
>    所以生产环境的 `--mute` 只关事件推送，每日战绩照推。
> 2. **`last_day` 边界 bug**：`last_day` 在**进程启动时**初始化为当天。若守护进程在 00:00
>    之后才启动，当天**不会**推前一天战绩，要等下一个 00:00。当前 KeepAlive 常驻不重启所以碰不到 ——
>    **但如果你以后改成定时重启 watch，每日推送会静默消失。**
>
> **若要建独立的定时任务 B，必须给 watch 加 `--no-daily-stats`**（改 plist 的
> `ProgramArguments` 再加一个 `<string>--no-daily-stats</string>`），否则**每天推两次**。

---

## 2. 三种实现路线

### 路线 1：macOS launchd `StartCalendarInterval`（推荐，真正的系统级）

**优点**：与常驻进程解耦、开机自启、可单独测试、有独立日志、系统原生。

**步骤**：

```bash
# ① 写 plist（模板见 §3）
vi ~/Library/LaunchAgents/com.daniel.5minbtc-daily-report.plist

# ② 语法校验（必做，plist 一个括号错就整个静默失败）
plutil -lint ~/Library/LaunchAgents/com.daniel.5minbtc-daily-report.plist

# ③ 确保日志目录存在（launchd 不会自动创建！）
mkdir -p ~/bb-auto/logs

# ④ 加载
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.daniel.5minbtc-daily-report.plist

# ⑤ 确认已注册
launchctl print gui/$(id -u)/com.daniel.5minbtc-daily-report | head -20

# ⑥ 立即测试一次（不必等到点）—— 这是唯一可靠的验证方式
launchctl kickstart -k gui/$(id -u)/com.daniel.5minbtc-daily-report

# ⑦ 看结果
tail -30 ~/bb-auto/logs/launchd-daily-report.out.log
tail -30 ~/bb-auto/logs/launchd-daily-report.err.log

# 回退
launchctl bootout gui/$(id -u)/com.daniel.5minbtc-daily-report
```

### 路线 2：cc-connect cron（一条命令，能推到当前 Telegram 会话）

**优点**：最快、能在群里收到结果、有 `/cron` 可查可停。
**缺点**：依赖 cc-connect 服务存活。

```bash
# 任务 B（shell 直跑，不走 LLM）
cc-connect cron add --cron "15 23 * * *" \
  --exec "/usr/bin/python3 /Users/daniel/.claude/skills/5minbtc/scripts/5minbtc_day_stats.py --push" \
  --desc "5minbtc 每日战绩"

# 任务 A（LLM 工作流型）
cc-connect cron add --cron "2,7,12,17,22,27,32,37,42,47,52,57 20-22 * * *" \
  --prompt "按 5minbtc skill 的标准流程跑一次预测并按 output-template.md 推送报告" \
  --desc "5minbtc 5min 预测" \
  --session-mode new-per-run --timeout-mins 10

# 管理
cc-connect cron list
cc-connect cron info <job-id>
cc-connect cron exec <job-id>          # 立即跑一次
cc-connect cron edit <job-id> enabled false   # 暂停（别删了重建）
cc-connect cron del <job-id>
```

> ⚠️ `--session-mode new-per-run` 让每次跑在**全新会话**里，避免上下文越滚越长。
> 任务 A 建议用它；任务 B 是 shell 命令，不涉及会话。

### 路线 3：hermes cron（Linux 机）

只有 hermes 机上才有的调度器（Mac 上 `which hermes` 为空）。用法见
[cron-llm-provider-failure.md](cron-llm-provider-failure.md)：
`hermes cron update --job-id <id> --model <m> --provider <p>` / `hermes cron run --job-id <id>`。
**注意**：这两个 job 的调度表达式与状态都记在该文件 §8，改动后要同步更新那张表。

---

## 3. plist 模板（定时型）

### 任务 B：每天 23:15 推**当天**战绩

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.daniel.5minbtc-daily-report</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/daniel/.claude/skills/5minbtc/scripts/5minbtc_day_stats.py</string>
        <string>--push</string>
    </array>

    <!-- 每天 23:15 (系统本地时间 = CST) -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>23</integer>
        <key>Minute</key><integer>15</integer>
    </dict>

    <!-- ⚠️ 定时任务不要配 KeepAlive -->
    <key>RunAtLoad</key>
    <false/>

    <key>ProcessType</key>
    <string>Background</string>

    <key>StandardOutPath</key>
    <string>/Users/daniel/bb-auto/logs/launchd-daily-report.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/daniel/bb-auto/logs/launchd-daily-report.err.log</string>
</dict>
</plist>
```

`day_stats.py` **不带 `--date` 时默认推「今日」**，所以 23:15 直接 `--push` 即可。

### 变体：00:05 推**前一天**

launchd **不做命令替换**，所以要用 shell 包一层（注意 macOS 的 date 语法是 `-v-1d`）：

```xml
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>/usr/bin/python3 /Users/daniel/.claude/skills/5minbtc/scripts/5minbtc_day_stats.py --date $(date -v-1d +%F) --push</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict><key>Hour</key><integer>0</integer><key>Minute</key><integer>5</integer></dict>
```

注意事项：

- macOS 的 `date` 用 `-v-1d` 取前一天（GNU 的 `-d yesterday` 在 macOS 上**不可用**）。
- plist 里 `%` 是**普通字符**，**不要**写成 `%%` —— 写成 `%%F` 会让 `date` 输出字面量 `%F`，
  结果 `--date %F` 查不到任何记录。这是本条变体最容易踩的坑。
- 加载后务必 `kickstart` 跑一次，确认日志里日期正确、不是 `%F`。

### 一天跑多次

`StartCalendarInterval` 接受**数组**：

```xml
<key>StartCalendarInterval</key>
<array>
    <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>15</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
</array>
```

---

## 4. 只跑一次 / 延迟一次（不要用 cron 表达这个）

- **cc-connect**：用 `cc-connect timer add --delay 2h --prompt "..."`（一次性，触发后自动归档）。
  **不要**用 cron 表达"只跑一次"——`30 14 10 9 *` 意思是"每年 9 月 10 日 14:30"，不是"今年这一次"。
- **launchd**：定时型 launchd 本身就是**长期重复**语义，没有"只跑一次"的原生表达。
  一次性任务建议用 `cc-connect timer`，或临时 plist + 跑完 `bootout`。

---

## 5. 坑清单（每条都实际踩过或实测过）

| # | 坑 | 说明与对策 |
|---|----|-----------|
| 1 | **定时型配了 `KeepAlive`** | 任务退出即被重启 → 疯狂循环。定时型**只配 `StartCalendarInterval`** |
| 2 | **launchd 不展开 `~`、不读 shell rc、PATH 极简** | 所有路径写**绝对路径**；python 用 `/usr/bin/python3`（引擎零第三方依赖，别用 brew/venv 的 python） |
| 3 | **日志目录不存在 → 静默失败** | launchd **不创建** `StandardOutPath`/`StandardErrorPath` 的父目录 → 先 `mkdir -p ~/bb-auto/logs` |
| 4 | **plist 语法错 → 静默不加载** | 每次改完必跑 `plutil -lint <plist>` |
| 5 | **机器睡眠错过时间点** | launchd 行为：**唤醒后补跑一次**（不像传统 cron 直接丢弃）。但可能延迟数分钟，别把它当精确时钟 |
| 6 | **重复推送** | watch 内置每日推送 + 独立定时任务 = 每天两次 → 给 watch 加 `--no-daily-stats` |
| 7 | **watch 的 `last_day` 启动边界** | 若改成定时重启 watch，每日推送会静默消失（见 §1 任务 B） |
| 8 | **`--mute` 不静音每日推送** | 它是 subprocess 直调，不走 `push()` 包装器。别以为 `--mute` 就什么都不会推 |
| 9 | **引擎/脚本改名后路径失效** | 2026-09-10 引擎已改名 `-v5.7.py` → `-v6.0.py`。任何 plist/脚本里的旧路径都要同步；launchd 不会报错，只会静默失败 |
| 10 | **静默失败最难查** | `5minbtc_realtime.py` 的 `run_engine()` 是 `except: return None` —— 路径错了**不报错、只不下单**。判断是否真在跑：`ps aux \| grep <脚本名>` 看子进程是否反复出现 |
| 11 | **新任务日志会一直长** | 定时任务每次追加日志 → 用 [setup-from-scratch.md §7](setup-from-scratch.md#7-日志轮转) 的月度轮转脚本一起归档 |
| 12 | **cron 表达式语义** | 5 段是 `分 时 日 月 周`。`*/5 * * * *` 才是"每 5 分钟"；`5 * * * *` 是"每小时的第 5 分钟" |
| 13 | **cc-connect cron ≠ 本会话的 CronCreate** | `cc-connect cron` 是持久化的 CLI 调度；会话内 CronCreate 的 job 随会话结束消失。做长期任务用前者 |

---

## 6. 验证清单（建完必须逐项过）

```bash
L=com.daniel.5minbtc-daily-report

# 1. plist 语法
plutil -lint ~/Library/LaunchAgents/$L.plist

# 2. 已注册且状态正常
launchctl print gui/$(id -u)/$L | grep -E "state|path|program"

# 3. 立即跑一次（不等时间点）
launchctl kickstart -k gui/$(id -u)/$L

# 4. 看输出（任务 B 应出现"📈 5minbtc 预测战绩"）
tail -20 ~/bb-auto/logs/launchd-daily-report.out.log
tail -20 ~/bb-auto/logs/launchd-daily-report.err.log   # 应为空

# 5. 确认 Telegram 真的收到

# 6. 隔天回来确认它自己按时跑过（看日志时间戳）
ls -la ~/bb-auto/logs/launchd-daily-report.out.log
```

**判据**：`kickstart` 能跑通 **≠** 到点会自动跑。第 6 步（隔天看时间戳）才是真正的验收。

---

## 7. 给 agent 的执行顺序

1. **先确认要哪个任务**（§1）。任务 A 在 Mac 上可能已被 realtime 覆盖 → **问清楚再动手**。
2. **选路线**：要系统级 / 与常驻解耦 → launchd；要最快且能进 Telegram → cc-connect cron。
3. **建之前先查重复**：`launchctl list | grep daniel` + `cc-connect cron list`，
   确认没有同类任务；建任务 B 前检查 watch 是否已带 `--no-daily-stats`。
4. **写配置 → `plutil -lint` → `bootstrap` → `kickstart` 测一次 → 看日志 → 确认收到**。
5. **隔天验收**（§6 第 6 步）。
6. **更新文档**：把新任务登记到本文件 §1 的表里，并在
   [setup-from-scratch.md §4](setup-from-scratch.md#4-launchd-常驻服务6-个) 的 job 表补一行。

---

## 8. 相关文档

- [setup-from-scratch.md](setup-from-scratch.md) — 从零搭建（依赖/目录/密钥/常驻服务/日志轮转）
- [cron-llm-provider-failure.md](cron-llm-provider-failure.md) — hermes cron 的 provider 失效诊断；§8 是 job 列表
- [output-template.md](output-template.md) — 推送内容格式（任务 A 的输出规范）
- [pitfalls.md](pitfalls.md) — #7 Cron Job 版本同步 / #18 K线开局概率不可信
