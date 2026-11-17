# 交易复盘 · YYYY-MM-DD（周X）

> 记录人：黎承祖 ｜ 助理：灵犀
> 数据来源：本人实盘记录 + 韭研公社异动解析（jiuyangongshe.com，爬取自当日）

---

## 一、今日操作

| 标的 | 方向 | 成交价 | 买入逻辑 |
|---|---|---|---|
| 标的1（代码） | 买入/卖出 | X.XXX | 用户自述逻辑 |

---

## 二、持仓策略（每日执行）

- 继续持有，静待涨停；
- **止损纪律：开盘跌幅 > -5% 则离场**；
- 其余情况继续持有。

---

## 三、标的产业逻辑核验（韭研公社异动解析）

### 3.1 标的1（代码）——用户逻辑 ✅/⚠️ 结论
- 异动解析 N 条 ｜ 相关文章 N 篇
- 题材标签：**…**
- 核心催化（异动解析原文，日期）：
  - 要点1（引用原文）
  - 要点2
- 结论：与买入逻辑吻合/不一致，说明。

### 3.2 标的2（代码）——用户逻辑 ⚠️ 站内另一条线
- 站内逻辑线 A：…
- 站内逻辑线 B（更硬的政策/事件催化）：…（点名该股的第一梯队/受益方向）
- 风险提示：买入依据是资金面/技术面 vs 站内基本面差异说明。

---

## 四、次日关注要点

1. 标的1：题材热度延续性（盘前解读/信息差是否继续点名）
2. 标的2：资金/连板情绪承接 + 政策催化节点（日期）
3. 严格执行止损纪律：**开盘跌幅 > -5% 离场**

---

## 五、明日计划

- 开盘前：查看盘前解读/信息差（韭研公社）确认标的是否继续被点名；
- 盘中：盯情绪与资金承接；
- 触发止损线无条件离场，不抱侥幸。

---

*本记录由灵犀整理，韭研公社数据为公开页面爬取（SSR），仅供个人复盘参考，不构成投资建议。*

---

## HTML 转换（Python）

```python
import markdown
html = markdown.markdown(open(src, encoding='utf-8').read(), extensions=['tables'])
# 套以下 style 块后写 .html 文件（注意 f-string 转义 {{ }}）
```

style 块要点：`body{max-width:760px;line-height:1.7;font-family:-apple-system,"PingFang SC",sans-serif;background:#fafafa}`；`h1{border-bottom:2px solid #e94560}`；`h2{border-left:4px solid #e94560}`；`table{border-collapse:collapse;width:100%;background:#fff}`；`th,td{border:1px solid #ddd;padding:8px 12px}`；`blockquote{border-left:4px solid #e94560;background:#fff5f5}`。输出文件同目录 `YYYY-MM-DD-复盘.html`，与 MD 一起发飞书。
