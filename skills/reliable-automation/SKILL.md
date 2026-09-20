---
name: reliable-automation
description: 让自动运转的 agent 团队不静默失败：定时/事件任务跑了没有、跑成功没有（watchdog 查产物与心跳）、重跑不重复副作用（idempotency）。适用：常驻 agent 任务、L3 人工闸门、失败可见性。
---

# Reliable Automation

让**自动运转的 agent 团队**不静默失败。补的是两件基础设施：**失败可见性**与
**幂等键约定**。

主线论断：

> **"持久稳定" ≠ "不失败"，= 失败了你知道 + 状态不丢 + 能重跑。**

对 agent 团队来说，这三件事分别意味着：

| 支柱 | 缺了会怎样 |
|---|---|
| 失败了你知道 | 定时任务跑了没有 / 跑成功没有，你只能靠"我好像没收到消息"判断 |
| 状态不丢 | 会话上下文一关，这次 run 等于没发生 |
| 能重跑 | 定时器重叠触发或失败重试，同一件事做两遍、token 花两份 |

核心洞察：**进程活着 ≠ 在工作，run 结束 ≠ 有产出，任务自己说成功 ≠ 成功。**
下面的检查一律围绕"最后一次成功产出"，而不是 PID，也不是任务的自我声明。

真实事故（完整记录见 [`references/design.md`](./references/design.md)）：

- 引擎的 `except Exception: return None` 吞掉全部异常，一次 SSL 失败后系统
  **6 小时零产出**，而错误日志是 **0 字节**；
- 推送脚本的 `subprocess.run` 包在 `except: pass` 里、路径写死指向一个已不存在的
  文件，`--telegram` 看起来在工作，实际什么都没发；
- 机器上 6 个常驻进程全部在跑，但**没有任何一个**写"我还在工作"的信号，
  也没有 watchdog。agent 侧的同一形态：run 跑完没产出、或跳过没说出口，
  人类看到的只有"没消息"。

## 三个工具

| 脚本 | 作用 | 一句话 |
|---|---|---|
| [`scripts/watchdog.py`](./scripts/watchdog.py) | 按声明式注册表检查"该发生但没发生" | 只读、零侵入；**不读任务的自我声明**，只看产出 |
| [`scripts/heartbeat.py`](./scripts/heartbeat.py) | 给任务写/读"我还在工作" | 原子写入；给没有稳定产物的长任务用 |
| [`scripts/idempotency.py`](./scripts/idempotency.py) | `claim(key)` → 是否首次 | 让重复触发/重试不产生第二份副作用 |

只用标准库，兼容 Python 3.10+（脚本本身在 3.9 上也能跑）。不引入任何 pip 依赖。

## 什么时候用它 / 不用它

适用：

- 团队已经有明确角色（例如本仓库的 14 个 C-suite + 92 个叶子），你**想让它们
  自动运转**而不是每次都要有人在会话里喊一句；
- 任务由定时器或事件触发，需要回答"**跑了没有、跑成功没有**"；
- 有不可逆动作（发布、资金、法律、对外声明）需要 **L3 人工闸门**；
- 发现过"我好像没收到消息"这类事故，但事后才反应过来。

不适用：

- 一次性的、交互式的会话工作——没有"持续产出"就没有可检查的新鲜度；
- 想用它替代监控平台（Prometheus / Grafana）——这里是单机、零依赖的轻量方案；
- 想让工具替你决定"哪一级动作需要人批准"。闸门的**判级**是治理决策，
  见 `references/design.md` 的原理 4；
- 想让工具自动修复问题。本 Skill 只做**发现**，不做自愈。

## 三分钟接入

第一步只需要一份注册表。注册表按"任务该产出什么"来描述，而不是按"任务怎么实现"——
所以对现有 agent 任务**零侵入**。
[`examples/watchdog.registry.json`](./examples/watchdog.registry.json) 是一份可直接改的样例
（里面的路径是**示例占位**，代表一类常见布局，接入时换成你自己的）：

```json
{
  "tasks": [
    {
      "name": "daily-review",
      "kind": "heartbeat",
      "path": "~/.local/state/heartbeats/daily-review.json",
      "max_age_seconds": 90000,
      "severity": "high",
      "note": "每天定时触发的 agent 任务；90000s≈25h，留出跳过一天的余量"
    },
    {
      "name": "weekly-report",
      "kind": "artifact",
      "path": "~/agent-sessions/latest/weekly-report.md",
      "max_age_seconds": 604800,
      "severity": "high",
      "min_bytes": 512
    }
  ]
}
```

跑一次：

```bash
python scripts/watchdog.py --registry examples/watchdog.registry.json --verbose
```

输出（人类可读表 + `--json` 机器可读 + `--verbose` 附 detail/note）：

```
TASK           KIND       STATUS        AGE  LIMIT  SEVERITY  DETAIL
daily-review   heartbeat  config-error  -    25.0h  high      注册表指向的路径不存在：…
weekly-report  artifact   ok            2.0h 7.0d   high      最后写入距今 2.0h

  合计：healthy=1，stale=0，empty=0，config-error=1，failed=0
```

`config-error` 在第一次接入时**大量出现是好事**——它精确指出"注册表说的路径
和磁盘上的现实不一致"，通常就意味着某个任务的产出根本不存在。

## watchdog.py

### 三种 kind

| kind | 判定依据 | 侵入性 | 用在哪 |
|---|---|---|---|
| `artifact` | 已有产物的 **mtime** | **零**：不用改任何现有 agent 代码 | 有稳定落盘产物的任务（优先选它） |
| `heartbeat` | 心跳文件里的 `ts` | 任务每轮调用一次 `heartbeat.py beat` | 长任务、事件驱动任务、没有稳定产物的场景 |
| `command` | 命令**退出码** | 需要一条判断命令 | 只有"在不在"能用命令表达的场景 |

### 状态词表

| status | 含义 | 该怎么办 |
|---|---|---|
| `ok` | 新鲜 | 什么都不用做 |
| `stale` | 超过 `max_age_seconds` 没更新 | 任务故障，去查 |
| `empty` | 产物小于 `min_bytes`（抓"文件在但被清空/写成空报告"） | 任务故障，去查 |
| `failed` | `command` 退出码非 0 或超时 | 任务故障，去查 |
| `config-error` | **注册表与磁盘现实不符**：路径不存在、指向目录、不可读、JSON 坏、字段缺失 | 改注册表或改产出，**不是任务故障** |

`config-error` 与 `stale` 必须分开报：混在一起会让一次路径写错变成永久告警，
进而导致告警疲劳——那正是"6 小时静默"能发生的真正原因。
默认"路径不存在 = config-error"；如果某个任务确实是"缺失即故障"，
显式写 `"on_missing": "stale"`。

### 退出码（给 launchd / cron 判读）

| 码 | 含义 |
|---|---|
| `0` | 全部健康 |
| `1` | 有任何异常（含 `config-error`；注册表本身读不到也算 1） |
| `2` | 命令行用法错误（argparse 的标准行为） |

### 告警出口

**默认不推送。** 有异常时用 `--alert-cmd` 交给使用者自己的推送脚本：

```bash
python scripts/watchdog.py \
  --registry ~/.local/state/agent-tasks/watchdog.registry.json \
  --alert-cmd 'printf "%s" "$(cat)" | /path/to/my-notify.sh'
```

- 告警全文同时从 **stdin** 传入，并替换命令里的 `{msg}` 占位符；
  用 stdin 的写法不带 `{msg}` 也可以，watchdog 会提醒一句但不影响执行；
- 告警命令的退出码会被检查：它失败本身也会让 watchdog 退出 1；
- 没有异常时**不会**执行告警命令。

挂到 launchd / cron 时建议 5 分钟一次。macOS 用 `StartInterval` 或
`StartCalendarInterval`，**不要用 `KeepAlive`**——watchdog 是一次性进程。

## heartbeat.py

给没有稳定产物的长任务 / 事件驱动任务用。任务每完成一轮写一次：

```python
from heartbeat import write_heartbeat  # 或直接调用 CLI
write_heartbeat("daily-review", note="第 120 轮")
```

```bash
python scripts/heartbeat.py beat daily-review
python scripts/heartbeat.py check daily-review --max-age 90000
python scripts/heartbeat.py list
```

- 写入是**原子**的（临时文件 + `os.replace`），读到的永远是完整 JSON；
- 目录优先级：`--dir` > `RELIABLE_HEARTBEAT_DIR` > `$XDG_STATE_HOME/heartbeats` >
  `~/.local/state/heartbeats`（所以心跳落在 agent 会话之外，会话结束不影响它）；
- 心跳名只允许 `[A-Za-z0-9._-]`，避免路径穿越；
- `check` 退出码：`0` 新鲜 / `1` 过期或缺失，可直接用在 shell 的 `&&` 链里。

## idempotency.py

让重复触发与失败重试变成安全动作。关键约定：

```
<task_type>:<entity>:<time_bucket>
```

| 例子 | 含义 |
|---|---|
| `daily-review:inbox:2026-09-16` | 今天这个收件箱只复盘一次 |
| `publish:weekly-report:2026-W38` | 这周这份报告只发布一次 |
| `approve:publish-2026-09-16:human` | 这条 L3 放行只记一次（闸门凭证） |

**先领凭证，再干活：**

```bash
python scripts/idempotency.py \
  --ledger ~/.local/state/agent-tasks/ledger.jsonl \
  claim 'publish:weekly-report:2026-W38' \
  && ./publish-report.sh
```

退出码：`0` = 首次（去干活）/ `1` = 已做过（跳过）。`set -e` 下天然安全。

Python 里：

```python
from idempotency import claim
if claim("daily-review:inbox:2026-09-16", ledger_path, ttl_seconds=86400):
    run_daily_review()
```

- 账本是 JSONL 追加写，用 `O_APPEND` + 单次 `os.write` + POSIX `flock`，
  并发调用不会撕裂行、也不会同时领到同一张凭证——定时器重叠触发时这一点很关键；
- `ttl_seconds` 给周期性任务：同一键在 TTL 内只允许一次，过期后可再来；
- `time_bucket` 由**调用方**决定：取粗会漏做，取细会重复做；
- `gc` 子命令可以清理过期键与坏行。注意它是"写临时文件 + `os.replace`"（换 inode），
  **只应在没有并发写入时运行**（例如 cron 的安静时段）。

## 和 agent 团队治理的接口

- **闸门（L3）**：自动化只能准备到"待批准"。批准这件事本身也应该是磁盘上的事实
  （用 `claim('approve:<action>:<bucket>')` 记一次），否则会出现"人批了 agent 不知道"
  或"agent 以为批了"两种失败。
- **不能自证**：`watchdog.py` 是外部检查者，**不解析任务的自我声明**。
  重要完成声明的独立复核属于 Governor 的职责（本仓库 `agents/governor/` 的岗位契约），
  不属于执行者自己。详见 `references/design.md` 的原理 5。
- **台账优先**：如果台账/队列文件本身停了，单个 run 的成功没有意义——
  所以注册表里应该有**一条**检查台账新鲜度的 `artifact` 项。

## 边界与不做的事

- **不做自愈**：不自动重启、不自动补单。没有护栏和停止条件的自动重启，
  会把"静默故障"升级成"静默重启循环"。
- **不判级**："什么算 L3"是团队治理决策，工具只负责把异常算出来。
- **不替代监控平台**：这是单机、零依赖的轻量方案。
- **不实现常驻循环**：`skills/` 不是 runtime；watchdog 由 launchd / cron 拉起。
- **不是运行证据**：结构检查通过不代表你的 agent 团队真的在健康运转，
  阈值和注册表要按自己的任务调。
- **watchdog 自己失联是已知盲区**：它没被拉起、或告警通道坏了，异常仍无人知晓。
  缓解方式见 `references/design.md`。

## 阈值怎么定

`max_age_seconds` 建议取正常产出间隔的 **3~5 倍**，并把**跳过场景**算进去
（周末不跑的任务按周设，不要按天设）。定太紧会抖动误报，误报直接导致告警疲劳——
宁可放宽，也不要制造噪声。

## 测试证据

三份标准库 `unittest` 测试，共 90 例，覆盖健康/过期/缺失/配置错误/坏 JSON、
心跳写入读取与原子性、幂等键的首次/重复/TTL 过期/并发追加/多进程竞争：

```bash
python scripts/test_watchdog.py
python scripts/test_heartbeat.py
python scripts/test_idempotency.py
```

这些是**结构证据**：它们证明脚本的行为符合约定，不证明任何具体 agent 任务
或守护进程的健康状况。

## 参考

- [`references/design.md`](./references/design.md) —— 五条原理、三个真实反例、取舍与盲区
- [`examples/watchdog.registry.json`](./examples/watchdog.registry.json) —— 可直接改的注册表示例
