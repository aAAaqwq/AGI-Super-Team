# 抖音脚本合同

## 必需输入

- `content_id`、受众、唯一判断、期望动作。
- 第一方证据和可展示屏录/画面，含权利、隐私与来源状态。
- 目标时长、出镜/无出镜选择、声音来源。

## 固定输出

| 时间 | 口播/字幕 | 画面动作 | 证据 | 权利/隐私 |
|---|---|---|---|---|
| 0–3 秒 | 单一 Hook | 问题或结果证据 | claim ID | 待核验项 |
| 主体 | 问题、连续步骤 | 屏录/卡片/实物 | evidence ID | 遮挡/授权 |
| 结尾 | 结果边界、下一步 | 验收或失败 | limitation | CTA 权限 |

同时输出 3 个 Hook 候选、字幕稿、镜头清单、素材缺口、人工朗读/表演检查和制作 handoff。

```yaml
status: script-ready-awaiting-human-performance-review
aspect_ratio: "9:16"
human_readthrough_complete: false
screen_privacy_review_complete: false
external_actions: none
```
