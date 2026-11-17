# 龙擎 Alpha Terminal（longqin.hanxai.cn）数据接入

自建的 A 股研究终端（`longqing-alpha-terminal`）。**这是选股流水线最好的起点** —— 它的主力池自带「控盘度 / 强度 / 加权分」，比外部接口的裸涨幅信息量大得多。

---

## 一、登录

```python
POST https://longqin.hanxai.cn/api/auth/login
Content-Type: application/json

{"username":"<LONGQIN_USERNAME>","password":"<LONGQIN_PASSWORD>"}
→ {"access_token":"eyJ..."}
```

凭证从环境变量 `LONGQIN_USERNAME` / `LONGQIN_PASSWORD` 读取，示例中不写真实密码。

**⚠️ 只有这一个路径。** 实测 `/api/v1/auth/login`、`/api/login`、`/auth/login`、`/api/v1/login` 全部 404。

后续请求带 `Authorization: Bearer <token>`（token 约 317 字符，有效期足够一次会话）。

---

## 二、核心端点

| 端点 | 用途 | 响应体量 |
|---|---|---|
| `GET /openapi.json` | **131 个端点的完整清单 —— 先拉这个再写代码** | 130 KB |
| `GET /api/v7/main-pool` | **主力池（作战池）** ⭐ | 50 KB |
| `GET /v1/market/snapshot` | 市场快照（指数 / breadth / turnover / 板块龙头） | 100 KB |
| `GET /api/v5/market-phase` | 市场阶段（SESSION_AM/PM、交易日、**服务器时间**） | 极小 |
| `GET /v1/market/daily-review` | 每日复盘（盘后才有内容，盘中为空） | — |
| `GET /v1/market/limit-rankings` | 涨跌停排行 | — |
| `GET /v1/snapshots/resonance/latest` | 最新四维共振快照 | — |
| `GET /v1/snapshots/control-pool` | 控盘池快照 | — |
| `GET /v1/snapshots/playbook` | Playbook 快照 | — |
| `GET /api/v5/candidates/latest` | 最新候选 | — |
| `GET /api/v4/stock/{code}` / `/kline` | 个股详情 / K 线 | — |
| `GET /v1/signals` | 信号列表 | — |
| `GET /v1/market/intelligence-pool` | 情报池 | — |

---

## 三、`/api/v7/main-pool` 字段语义

```json
{"date":"20261027","minute":"13:18","quality":"DEGRADED",
 "returned_count":93,"items":[ ... ]}
```

单条 item 的关键字段：

| 字段 | 含义 | 怎么用 |
|---|---|---|
| `code` / `name` | `600826.SH` 形式，**带深浅市后缀** | 丢给腾讯前必须拆 `.SH`→`sh` |
| `pct` | 当日涨幅 % | 判是否已涨停（≥9.5 直接排除，买不进） |
| **`control`** | **控盘度**（约 0–140） | ⭐ **>100 = 强控盘；<10 = 强度再高也控不住盘** |
| **`strength`** | 强度分 | ⚠️ **高不等于会涨**，见 Pitfalls |
| **`weighted_score`** | 加权总分（0–1） | ⭐ **主排序依据**，>0.7 才算候选 |
| `high_prob` | 系统判定高概率 | ⚠️ **经常整池全 false**，别当结论 |
| `trigger` / `triggered` | 触发时间 / 是否触发 | 越早（9:30 附近）越强 |
| `bursts` | 脉冲次数 | 辅助 |
| `blast` | 炸板次数 | 配合开板判据 |
| `controlTime` | 控盘时长（分钟） | 辅助 |
| `efficiency` | 效率 | 辅助 |
| `industry` | 行业（池内口径） | 结构轴分组，**与涨停池 hybk 口径不同** |
| `minutes` | 已交易分钟数 | — |
| `source_coherence` | 数据一致性 | `COHERENT` 才可信 |
| `missing_fields` | 缺失字段列表 | 常见缺 `sector` |

**筛选模板**：

```python
cand = [x for x in items
        if x["pct"] < 9.5                    # 未涨停（买得进）
        and (x.get("control") or 0) >= 40    # 控盘够
        and (x.get("strength") or 0) > 0]    # 强度为正
cand.sort(key=lambda y: -(y.get("weighted_score") or 0))
```

---

## 四、`/v1/market/snapshot` 的 breadth —— 判断「今天能不能做多」最快的指标

```python
d = GET /v1/market/snapshot
d["observations"]["breadth"]     # {"advancers":1156,"decliners":4303,"flat":118,"observed_count":5577}
d["observations"]["index"]["items"]        # 三大指数（current / pct_change / provider_observed_at）
d["observations"]["turnover"]["amount_cny"] # 成交额（单位：元）
d["observations"]["sector_leaders"]["items"] # 板块强度排行
```

**判据（写进结论前必查）**：

| 涨跌比 | 含义 | 行动 |
|---|---|---|
| advancers : decliners > 1.5:1 | 普涨 | 可正常做多 |
| 1:1 ~ 1:2 | 分化 | 只做最强 |
| **< 1:2** | **弱势** | 追涨建议全部打折 |
| **< 1:3** | **极弱** | 只减不加，明确提示风险 |

实测 2026-10-27 13:08：**1156 涨 vs 4303 跌（1:3.7）**，创业板从早盘 +0.89% 转到 −1.10%。当天所有「追涨」结论都该附上这个前提。

---

## 五、Pitfalls（都是实测踩过的）

- **`quality` 可能是 `DEGRADED`**，`missing_fields` 会列出缺什么（常见缺 `provider_timestamp`、`main_net_inflow`）。DEGRADED 时**不能当唯一依据**，必须用腾讯/东财实时数据交叉验证。
- **`high_prob` 常年整池为 false**。系统保守，不代表没机会；反过来也别自作聪明把 false 当 true。2026-10-27 93 只里 0 只 high_prob。
- **`strength` 会骗人**：2026-10-27 慈文传媒 `strength` 39.86（池内第二高），实际当天 −4.18%、外盘仅 35.8%、跌破 MA5/MA10。**`strength` 高 + `control` 低 = 危险组合**（控不住盘的高强度＝有人在对倒）。
- **`industry` 不等于涨停池的 `hybk`**。算结构轴要用东财涨停池的 `hybk` 行业分布，两者口径不同（池内写「照明设备Ⅱ」、涨停池写「照明设备」）。做匹配时取前 2-4 字比较。
- **`code` 带 `.SH/.SZ` 后缀**，直接丢给 `qt.gtimg.cn` 会失败，必须转换。
- **服务器时间比本地可靠** —— 用 `/api/v5/market-phase` 的 `server_time` 判断「现在盘中还是盘后」，别用容器 `date`（容器是 UTC）。
- **`/v1/market/daily-review` 盘中返回空**，盘后才有内容。

---

## 六、与外部涨停池的配合（结构轴）

龙擎池的 `industry` 用来分组，但**结构轴要的是「同行业今天有几只涨停」**，这个数据来自东财涨停池：

```python
GET https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989
    &dpt=wz.ztzt&Pageindex=0&pagesize=400&sort=fbt%3Aasc&date=YYYYMMDD
# 字段：c(代码) n(名称) hybk(行业) lbc(连板) fund(封单额) fbt(首封时间) zbc(炸板) hs(换手)
```

```python
from collections import Counter
zt_ind = Counter(x.get("hybk") for x in pool)   # 结构轴：同行业涨停家数
```

**2026-10-27 实测**：汽车零部件 **13 只涨停**（一家独大）→ 只有这个板块的票结构轴能拿满分。同日「照明设备」0 只涨停，海洋王即便涨 9.24% 结构轴也是 −2。

---

## 七、实测案例：四维共振筛池（2026-10-27）

池内 93 只 → 粗筛（未涨停 + 控盘≥40 + 强度>0）30 只 → 取 TOP11 算四维：

| 名称 | 涨幅 | 流通亿 | 换手 | 量/5日 | 同业涨停 | 时间轴 | 结构轴 | 量价轴 | 合计 |
|---|---|---|---|---|---|---|---|---|---|
| 湖南天雁 | +4.73% | **64.4** | 5.9% | **0.78** | **13** | +1 | +2 | +1 | **+4** |
| 模塑科技 | +5.05% | 126.0 | 12.8% | 1.45 | **13** | 0 | +2 | +1 | **+3** |
| 海洋王 | **+9.24%** | 73.6 | **25.3%** | 1.48 | **0** | 0 | **−2** | +1 | **−1** |

**最重要的一条结论**：**涨幅最大的海洋王（+9.24%），共振分是 −1（倒数）。** 因为照明设备 0 只涨停＝独苗，换手 25.3%。这是「单点爆发」不是「共振」—— 与 2026-10-23 明月镜片（+20% 但独苗+天量，次日只涨 4.81% 未封板）完全同型。

**第二重要的**：共振分最高的湖南天雁（+4）反而有两个硬伤 —— `PE −271.80`（亏损）+ 涨停后资金流出（10/22 +3.45 亿 → 之后 4 天净流出）。**技术形态好但钱在撤 ≠ 可以买。** 相比之下模塑科技共振分低 1 分，但资金两天进 7.92 亿、PE 25.16、距 250 日高 −23.5%。**「钱在进」比「形态好看」更硬。**
