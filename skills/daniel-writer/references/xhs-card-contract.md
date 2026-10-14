# 小红书卡片编辑合同

## 结构选择

- 教程：问题 → 3–7 步 → 验收 → 失败分支。
- 失败复盘：预期 → 失败证据 → 最小修复 → 重测 → 未知。
- 对比：同一任务与口径 → 差异 → 选择边界。
- 证据清单：结论 → 多项第一方证据 → 可复现入口。

## 固定输出

- `cover`: 单一承诺、主标题、视觉对象、证据线索。
- `cards`: 6–10 张；每张仅一个任务，含 `claim_ids`。
- `caption`: 背景、适用边界、来源和低摩擦 CTA。
- `emoji_plan`: 3–6 个互不重复的 emoji，逐项记录唯一使用位置、段落任务与去除后的可读性检查。
- `hashtags`: 4–8 个强相关候选，覆盖任务/人群、痛点/方法、工具/场景，并列出发布日复核项。
- `visual_qa`: 3:4、安全区、缩略图、字号、对比、权利。
- `rule_unknowns`: 标签、AI 标识、链接、频率等动作时核验项。

```yaml
status: candidate-ready-awaiting-human-visual-review
aspect_ratio: "3:4"
claim_evidence_complete: false
human_visual_review_complete: false
external_actions: none
publishing_authorization: none
```

不得用内部候选评分预测点击、收藏、涨粉或平台推荐。

不得在同一篇笔记或同一卡组内重复 emoji，不得用 emoji 代替证据、风险文字或卡片层级；不得用 `#必火`、`#热门`、`#流量密码` 等标签暗示未经验证的分发效果。
