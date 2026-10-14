---
name: video-benchmark-breakdown
description: "对标视频拆解流水线：把竞品/爆款视频（B站/YouTube/抖音/快手/X 等）下载或提取→转写逐字稿→结构化拆解剧情、高光与脚本。适用「拆解这条爆款视频」「对标账号视频分析」「把竞品视频转成逐字稿」；不用于下载受版权保护内容用于再分发或规避平台限制。"
---

# 视频对标拆解

三段式流水线，按顺序取用。每一步的完整能力见对应技能：

```
① 提取 doubao-video-extract  →  ② 转写 video-transcriber  →  ③ 拆解 byted-mediakit-video
```

| 步骤 | 能力 | 位置 |
|---|---|---|
| ① 提取 | 下载/解析在线或本地视频，拿到音频、字幕、画面元信息 | [`../doubao-video-extract/SKILL.md`](../doubao-video-extract/SKILL.md) |
| ② 转写 | 有字幕取字幕，无字幕下音频 + whisper 转写逐字稿 | [`../video-transcriber/SKILL.md`](../video-transcriber/SKILL.md)（仓库顶层已有技能） |
| ③ 拆解 | 剧情结构化、高光/精彩段拆条、场景语义分段、画面文字识别 | [`./byted-mediakit-video/SKILL.md`](./byted-mediakit-video/SKILL.md) |

## 使用纪律

1. 只对**有权限获取**的公开视频使用；不得用于规避平台保护或再分发受版权保护内容。
2. 拆解产出用于**学习结构与选题**，不是复制原文。
3. 引用竞品数据/结论时标注来源，不冒充自有素材。
