---
name: longqin-alpha-terminal-ops
description: "Use when 登录龙擎 longqin.hanxai.cn 拉作战池/市场快照/候选，结合选股框架出结论。"
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [ashare, 龙擎, longqin, 作战池, 主力池, api, 选股, 快照]
---

# 龙擎 Alpha Terminal 取数（longqin.hanxai.cn）

用户（黎承祖）自建的 A 股研究终端。**「作战池」= `/api/v7/main-pool`（官方叫主力池）**，是用户问
「结合我们的作战池和市场数据选股」时的数据源。

**定位**：龙擎提供**盘面事实 + 系统打分**；选股方法论在 `youzi-stock-quality-screen` /
`ashare-volume-resonance-analysis`。**不要把龙擎的分当成结论** —— 它自己也常返回 `high_prob=0`、
`quality=DEGRADED`。

## 触发条件
- 「登陆 longqin.hanxai.cn / 龙擎」「看看作战池」「主力池里有没有好的」
- 要求「结合我们的作战池和市场数据」选股
- 需要盘中真实市场宽度（涨跌家数）而不是只看指数
- 需要系统自己的控盘/强度/加权分做交叉验证

## 连接（2026-10-27 实测可用）

凭证只从环境变量读取：`LONGQIN_USERNAME`（默认 `admin`）与 `LONGQIN_PASSWORD`。
不要把用户名、密码写进脚本、提示词或日志。

```python
import os, urllib.request, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
BASE = "https://longqin.hanxai.cn"
UA   = {"User-Agent":"Mozilla/5.0","Content-Type":"application/json"}

# ① 登录（注意是 /api/auth/login，不是 /api/v1/auth/login）
body = json.dumps({"username": os.environ.get("LONGQIN_USERNAME", "admin"),
                    "password": os.environ["LONGQIN_PASSWORD"]}).encode()
r = urllib.request.Request(BASE+"/api/auth/login", data=body, headers=UA, method="POST")
tok = json.loads(urllib.request.urlopen(r, timeout=20, context=ctx).read())["access_token"]

# ② 带 Bearer
def lq(path, timeout=40):
    req = urllib.request.Request(BASE+path, headers={"User-Agent":"Mozilla/5.0",
                                                     "Authorization":"Bearer "+tok})
    return json.loads(urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode())
```

- 认证是 **JWT Bearer**，token 约 317 字符，不落盘也行（一次脚本跑完）。落盘 `/tmp/lq_tok.txt` 会在重启后失效，重登即可。
- 端点清单随时可查：`GET /openapi.json`（实测 131 个端点，返回 130KB，别整份塞进上下文——按关键词过滤 paths）。

## 关键端点

| 用途 | 端点 | 说明 |
|---|---|---|
| **作战池/主力池** | `GET /api/v7/main-pool` | **核心**，~93 只，见下方字段表 |
| 市场宽度+指数 | `GET /v1/market/snapshot` | `observations` 里含 breadth / index / turnover |
| 市场阶段+服务器时间 | `GET /api/v5/market-phase` | **先用它校准时间**，见 Pitfalls |
| 候选池 | `GET /api/v5/candidates/latest`、`/history` | |
| 个股详情/K线 | `GET /api/v4/stock/{code}`、`/api/v4/stock/{code}/kline` | |
| 四维共振快照 | `GET /v1/snapshots/resonance/latest` | 与 `ashare-volume-resonance-analysis` 同源思路 |
| 控盘池快照 | `GET /v1/snapshots/control-pool` | |
| Playbook | `GET /v1/snapshots/playbook` | |
| 每日复盘 | `GET /v1/market/daily-review`（`/full`、`/export.csv`、`POST /narrative`） | |
| 涨停排行/产业逻辑 | `GET /v1/market/limit-rankings`、`/v1/market/industry-logic` | |
| 信号 | `GET /v1/signals`、`/v1/signals/deliveries` | |
| PAPER 组合 | `GET /v1/paper/portfolio/stocks` | |

### `/api/v7/main-pool` 字段表

顶层：`date`（如 `20261027`）、`minute`（如 `13:06`）、`quality`、`generation`、`returned_count`、
`coverage_ratio`、`quality_issues`、`omitted_symbols`、`source_coherent`、`items[]`。

单个 item：

| 字段 | 含义 | 用法 |
|---|---|---|
| `code` / `name` | `600826.SH` 格式 / 名称 | 转腾讯时 `sh`+前6位 |
| `pct` | 实时涨跌幅 | **`pct >= 9.5` 即已涨停，做可买性筛时先排除** |
| `price` | 现价 | |
| **`control`** | **控盘分**（实测 5~139） | **最重要**，越高越像主力控盘 |
| `strength` | 强度分（实测 −0.27~46） | **强度高 ≠ 控盘好**，见 Pitfalls |
| **`weighted_score`** | **加权总分 0~1** | 池内排序主键，`>0.7` 算强 |
| `high_prob` | 系统判定高概率 | **常全为 false/0 只**，别硬找 |
| `triggered` / `trigger` | 是否触发 / 触发时间 `09:30` | 早触发 + 高控盘 = 强 |
| `bursts` / `blast` | 爆发次数 / 最近一次 | |
| `controlTime` / `minutes` | 控盘持续分钟 / 已交易分钟 | `controlTime/minutes` 越高越持续 |
| `industry` | 行业（常可用） | 做结构轴 |
| `sector` | 板块（**常为 null** + 记在 `missing_fields`） | 别依赖它 |
| `efficiency` | 效率 | |
| `source_coherence` | `COHERENT` 等 | |

### `/v1/market/snapshot` 的结构（⚠️ 不是列表）

```python
d = lq("/v1/market/snapshot")
o = d["observations"]            # ← dict，不是 list！
o["index"]["items"]              # [{code,name,current,pct_change,previous_close,symbol}]
o["breadth"]                     # {"advancers":1156,"decliners":4303,"flat":118,"observed_count":5577}
o["turnover"]["amount_cny"]      # 922624629424 ≈ 9226 亿
o["sector_leaders"]["items"]     # 板块强度排行（quality 常 DEGRADED）
```

`d["quality"]` = `GOOD`，`d["reasons"]` 常见 `LAST_TRADE_WINDOW_OBSERVATION` /
`PROVIDER_TIME_SKEW_EXCEEDED` / `INDEX_TIME_SKEW_EXCEEDED` —— 这些是「数据有轻微时延」，不是接口坏了。

## 标准取数流程（用户要「结合作战池选股」时）

```
① GET /api/v5/market-phase        → 拿 server_time 确认真实时间/是否盘中
② GET /v1/market/snapshot         → 涨跌家数（决定今天该不该做多）
③ GET /api/v7/main-pool           → 池内 93 只
④ 池内排序：先看 high_prob（常空）→ 再按 weighted_score 降序
⑤ 硬筛：pct < 9.5（未涨停）+ control >= 40 + strength > 0
⑥ 结构轴用**全市场涨停池**（东财 getTopicZTPool），不要用池内行业分布
⑦ 剩下的逐只拉腾讯实时 + K线，算四维共振（ashare-volume-resonance-analysis）
⑧ 输出时给「系统分 + 我的判断」两栏，不一致就说不一致
```

## Pitfalls

- **⭐ `observations` 是 dict，用 `obs[:8]` 会 `KeyError: slice(None,8,None)`**（本会话踩过）。
  先 `type()` 再遍历，或直接 `o["index"]["items"]`。
- **⭐ 容器时区是 UTC，龙擎的 `server_time` 才是北京时间真相**：本会话靠 `/api/v5/market-phase`
  才发现「现在是 13:07 盘中」而不是我以为的早上（也发现过已 19:45 收盘）。
  **任何「今天/盘中/收盘后」的判断，先读 market-phase，不要用 `date` 命令。**
- **⭐ `strength` 高不代表能买**：兰生股份 600826 强度 46.04（池内最高），但 `control` 只有 5，
  当天开盘封 9.02 后砸到 8.56（−5.1%）是**炸板派发**。**排序用 `weighted_score` + `control`，
  不要用 `strength` 单独下结论。**
- **`high_prob` 经常是 0 只**：系统自己不给高置信度标的。**不要为了凑数把普通票包装成「系统高概率」。**
- **`quality=DEGRADED` 时 `sector` 会缺失**（记在 `missing_fields:["sector"]`），结构轴必须外挂东财涨停池补。
- **不要整份 dump `/openapi.json`**（130KB）—— 按 `pool/market/candidate/resonance/snapshot/signal` 关键词过滤后只打印 path+method+summary。
- **池内行业分布 ≠ 今日热点分布**：池是「有异动的票」，涨停池是「已封板的票」。结构轴（同行业涨停家数）
  必须用涨停池算。实测 10/27 池内 TOP 是通用设备/汽车零部件各 7 只，但涨停池是汽车零部 13 只、一般零售 4 只。
- **不要用龙擎的 `pct` 当收盘价**：那是 `minute` 时刻的快照。要给用户价位，一律再用腾讯拉一次实时/收盘。
- **⭐⭐ `ltsz`（流通市值）在 main-pool 里恒为 `None`**（2026-10-28 实测 102/102 全缺）。用池内字段做
  「流通 30-100 亿」这道筛会返回 **0 只**，会误判成「池内全都涨停了」——**这是假信号，不是市场结论**。
  必须用腾讯 `qt.gtimg.cn` 的 `f[44]` 逐个补齐后再筛。
- **⭐⭐ 开盘 2 分钟内的池数据不可信**：2026-10-28 09:32 实测 `control` 只有 **1-3**、TOP1
  `weighted_score` 仅 **0.547**、`quality=DEGRADED`；同一批票在 09:45 后 `control` 回到 12-16、
  `weighted_score` 回到 0.6-0.81。**➜ 10:00 前拿到的「高分票」必须与腾讯实时行情交叉验证后再下结论，
  并向用户声明「数据分钟 + 质量 DEGRADED」。**

## 输出纪律

- 先说**市场宽度**（涨跌家数），再说个股 —— 用户要知道「今天该不该做」。
  实测 10/27 是 上涨 1,156 / 下跌 4,303（1:3.7），这种盘面任何票胜率都要打折，必须先讲。
- 系统分和我的判断**分两栏并列**，不一致时明确写「系统给 X，但我不认同，因为 Y」。
- **用户问「明天必涨」时，直接说没有必涨**，然后给排序 + 每只一个估计概率（并说明概率低于平时，理由是大盘宽度）。
  实测用户接受这种回答；不给概率只给清单会被追问「有没有机会」。

### ⭐⭐ 锁仓强度与可买性是反向的 —— 输出必须二选一

从主力池/涨停池筛出候选后，判封板牢不牢看三个数：

| 指标 | 极致锁仓 | 还在换手 | 取法 |
|---|---|---|---|
| **量比** | **< 0.5** | > 2 | 腾讯 `f[49]` |
| **换手率** | **< 3%** | > 10% | 涨停池 `hs` |
| **封单 ÷ 流通市值** | **≥ 3%** | < 1% | `fund ÷ (f[44]×1e8)` |

**但这三个数越极端，明天越买不进**：

```
量比 0.32 + 换手 2% + 封单 6%  → 最强锁仓 → 明天一字 → 只能看
量比 2.5  + 换手 12% + 封单 1% → 封得不死 → 明天开板给机会 → 能做
```

**用户明确批评过**：一次筛出三只全封死一字板（卖 1-3 全为 0、封单 11–39 万手），
用户直接说「**根本买不进选的没用**」。

**规则**：给候选时二选一写明，不许混着说 ——「能买但形态一般（给买点）」或
「形态最好但买不进（明天大概率一字，放弃）」。
实测：光洋股份 002708 量比 0.52 缩量涨停 + 封单 9.88 万手 = 形态最好，但换手仅 3.87%
→ 结论是「买不进」，不是「强烈推荐」。

### 硬筛补充：股东户数是连板否决项

`RPT_HOLDERNUM_DET` 的 `HOLDER_NUM_RATIO`：近 1–2 期减少/持平 → 能接力；
**单期 +30% 以上 → 直接剔除，不管几板多强**。
实测 10/27：阳光乳业 2 板但户数 **+56.3%**、襄阳轴承 4 板但 **+39.8%** → 都是散户接盘；
留下的多伦科技（−1.1%）、光洋股份（−8.8%）都是集中。

> **配套接口速查见 `references/data-enrichment-apis.md`**：东财财务（`RPT_LICO_FN_CPD` 唯一可用，
> `RPT_F10_FINANCE_MAINFINADATA`/`MainTargetAjax` 会静默返回全 `None`）、腾讯实时字段表
> （内盘/外盘/流通市值/量比索引）、分钟线取突变点、日周 K 线，以及「盘前取 `k[-2]` 会拿到前天」的 bug。

## 盘中临场判定口径（用户反复问的四件事）

### ① 开板了，是分歧还是出货？——六判据

| # | 判据 | 🟢 分歧（洗盘，可进） | 🔴 出货（派发，别碰） |
|---|---|---|---|
| **1** | **能否快速回封**（最关键） | **5-15 分钟内回封** | 迟迟不回 / 收盘没回 |
| **2** | 开板最低距涨停价 | **−2% 以内**（承接强） | **−5% 以上**（抢跑） |
| **3** | 开板时量能 | 温和（<封单量 30%） | 突然放天量 |
| **4** | 回封后量能 | **缩量**（锁住） | 持续放量（还在换手） |
| **5** | 炸板次数 | 1-2 次（考验后通过） | 3 次以上 |
| **6** | 当天资金流 | 净流入 | 大额净流出 |

> **口诀：开板不可怕，「开板后回不回得来」才是关键。能回封 = 弱手换强手；回不来 = 主力派发。**

**实测 2026-10-27**：东方海洋（2板，开板 −2% 后 **3 分钟**回封）、秦安股份（4 分钟）、襄阳轴承（7 分钟）
→ 全判真分歧。同日兰生股份开在涨停 9.02 后砸到 8.56（**−5.1%**）不再回封 + 池内 `control` 仅 5 → 判炸板派发。

### ② 主力还在吗？——必须答三态，不要答二元

| 状态 | 特征组合 | 应对 |
|---|---|---|
| **主力在（加仓）** | 资金**连续多日递增** + 外盘>内盘 + 缩量上涨 + 站上均线 | 可持有 |
| **主力在（换手/减）** | 单日大进但次日流出 + **内盘>外盘** + 冲高回落 + 买盘极薄 | 减仓，不加 |
| **主力撤（走完）** | 连续净流出 + 龙虎榜净卖 + 破均线 + 股东户数暴增 | 清仓 |

**核心区分：「连续递增」≠「单日暴增」**

| 形态 | 实例 | 含义 |
|---|---|---|
| 连续递增 1.17 → 1.72 → **3.89** 亿（越进越多） | 正裕工业 10-22~26 | 主力持续加仓 = **强续板信号** |
| 单日 +8.00 亿后转 −0.52 / −2.32 / −2.53 亿 | 示例股A 10-20~23 | **拉高派发** |

**「在换手」的实战识别（2026-10-28 示例股B）**：10/27 涨停进 0.958 亿（超大单 0.375 亿）→ 主力在；
但当日冲高 12.80 回落 12.52、内盘 88,052 > 外盘 76,135（主动卖多 15.7%）、**买1 仅挂 30 手** →
答「主力在，但今天在换手，减仓不加」。

### ③ 乖离率过热（最容易踩的追高坑）

| 现价相对 MA5 | 判定 |
|---|---|
| +3% ~ +8% | 🟢 健康上涨 |
| **> +10%** | 🔴 **短线透支**：趋势没坏也会横盘 2-3 天消化，**禁止追高** |

**实测 2026-10-28 示例股B**：12.52 / MA5 11.19 = **+11.87%** → 判「趋势健康但过热，只设止损不加仓」。
用户当日恰在 **12.70** 买入（全天仅 3 分钟价格 ≥12.70）—— 偏离 MA5 超 10% 时追高的典型代价。
**➜ 给买点建议时，先算「现价 ÷ MA5 − 1」，> 10% 必须明确写「这个位置不能追」。**

### ④ 共振 ≠ 涨幅大

| 案例 | 涨幅 | 池分 | 四维共振 | 原因 |
|---|---|---|---|---|
| **海洋王 002724**（10-28） | **+9.24%（全场最高）** | **0.815（池内最高）** | **−1（倒数）** | 照明设备板块 **0 只**涨停（独苗）+ 换手 25.3% |
| 明月镜片 301101（10-23） | +20% | — | 降级 | 文娱用品独苗 + 8.84 倍天量 → 次日仅 +4.81% 未封板 |

**➜ 「涨幅第一 + 系统分第一」也可能是单点爆发。判断依据必须是结构轴（同行业涨停家数），不是涨幅。**

---

> 框架细节见 `youzi-stock-quality-screen`（五标准+可买性）、`ashare-limitup-streak-analysis`（连板/龙一）、
> `ashare-volume-resonance-analysis`（四维共振）。龙擎只提供**事实与系统分**，方法论在那边。
