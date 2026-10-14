# 公众号编辑合同

## 必需输入

- `content_id`、目标读者、唯一承诺。
- Daniel 本人观点与提纲/关键决策。
- 主张—证据映射、来源 SHA/路径、权利与隐私状态。
- 禁止表达、期望 CTA、当前规则未知项。

## 固定输出

1. `editorial-brief`：读者任务、核心判断、证据与反声明。
2. `article-candidate`：标题候选、摘要、正文、配图位、来源。
3. `claim-evidence-table`：逐条标记 fact / judgment / hypothesis。
4. `mobile-preview-checklist`：段落、层级、图片说明、链接、错别字。
5. `daniel-line-review`：逐行 approve / revise / remove，默认全部 pending。

```yaml
status: candidate-ready-awaiting-daniel-line-review
daniel_authored_thesis: true
daniel_authored_outline_or_decisions: true
human_line_review_complete: false
external_actions: none
publishing_authorization: none
```

上述两个 authored 字段必须由可回链材料支持，不能接受稿件内自报。动态字数、功能、AI 标识和发布规则只记录为待官方核验项。
