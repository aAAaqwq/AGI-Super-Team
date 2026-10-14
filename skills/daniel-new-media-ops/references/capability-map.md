# 能力地图

## 创作

- `daniel-writer`：品牌声音、真人质感、证据边界、公众号/小红书/X/知乎/B站/抖音模板。
- `article-to-infographic`：判断哪些段落值得视觉化，并生成图片类型、信息节点、尺寸与提示词方案。
- `content-cover-gen`：目标库已有，负责平台封面。
- `content-typography`：目标库已有，负责中文排版和层级。

## 视频

- `integrate-opencut`：当前重写版 OpenCut 仓库集成。
- `integrate-opencut-classic`：旧版网页编辑器仓库的环境、构建与功能验证。
- `ffmpeg-video-editor`：常见剪辑、字幕、转码与抽帧命令；交付验证仍需针对实际文件执行。

## 发布

- `daniel-auto-publish`：发布简报、声明、风险检查和平台流程。
- `real-browser-social-publisher`：其支持的平台可见浏览器填写、草稿保存和内容管理页核验；不覆盖 X 普通帖、公众号文章和知乎。
- `x-article-publisher`：X Article 专用发布流程。
- `xhs-publisher`、`douyin-smart-publish`：目标库已有的平台专用发布能力。

## 去重结论

以下能力不并入 `daniel-writer`：发布自动化、浏览器控制、视频剪辑。它们会改变外部状态或有较大上下文体积，应继续作为独立 Skill，由总控按需加载。
