---
name: daniel-new-media-ops
description: 路由 Daniel 新媒体内容从选题、写作、视觉化、视频制作到多平台草稿与发布核验。适用于用户要求制作或分发 Daniel 品牌内容时；单纯文案润色优先直接使用 daniel-writer。
---

# Daniel 新媒体总控

目标是把一次内容生产组织成可审核、可追溯、可停止的工作流。不要在此复制子 Skill 的详细规则，只加载当前阶段需要的能力。

## 本项目日常入口与优先级

在 `/Users/danielli/新媒体运营` 使用时，先读 [项目契约](/Users/danielli/新媒体运营/AGENTS.md) 和 [使用指南](/Users/danielli/新媒体运营/运营系统/使用指南.md)。自然语言“运营启动 / 素材入库 / 今日选题 / 写核心稿 / 适配 / 审稿 / 发布准备 / 复盘”按指南解析当前阶段，不是后台命令。

所有 Daniel 个人 IP 任务先应用本地自媒体心法及 IP 事实与边界；正式写作的阶段、版本、单平台专家与批准由本地 `daniel-content-writing-style` 管理。`daniel-writer` 提供当前阶段的写法与资源，平台模板延后到当前核心稿获批后的适配阶段。不得以“统一写作入口”跳过任何门。当前两周主平台为公众号（用户于 2026-10-12 选择）；不预先授权选题、观点、内容版本或外部操作。

按当前任务只加载必要资源。素材/选题阶段不加载平台模板，纯审稿不自动改写。任务状态写回 [运营看板](/Users/danielli/新媒体运营/运营系统/任务模板.md)，先推进已有任务。

## 路由

1. 写作、改写、平台适配：读取同级 `../daniel-writer/SKILL.md`。
2. 文章配图与信息卡规划：读取 `../../article-to-infographic/SKILL.md`；封面可复用目标库已有的 `content-cover-gen`。
3. OpenCut 代码仓库工作：当前重写版读取 `../../integrate-opencut/SKILL.md`；旧版网页编辑器读取 `../../integrate-opencut-classic/SKILL.md`。实际视频时间线操作须以打开的编辑器界面和实测结果为准，不能从仓库集成 Skill 推断已经完成剪辑。
4. 文件级剪辑、转码、抽帧或导出验收：读取 `../../ffmpeg-video-editor/SKILL.md`。
5. 发布准备与平台安全门：读取同级 `../daniel-auto-publish/SKILL.md`。
6. 在 `real-browser-social-publisher` 明确覆盖的平台发布视频或图文时，读取 `../../real-browser-social-publisher/SKILL.md`；它当前没有 X 普通帖、公众号文章和知乎的专用流程。
7. 发布 X Article 时读取 `../../x-article-publisher/SKILL.md`；普通 X 帖不等同于 Article。

平台已有专用 Skill 时优先使用：小红书用 `xhs-publisher`，抖音用 `douyin-smart-publish`。不要让通用浏览器流程冒充专用适配器。

`daniel-auto-publish` 当前覆盖小红书和部分视频平台；其公众号部分提供排版预览，不代表可以自动群发。X 普通帖与知乎仍需另行核实可用发布工具或在可见界面操作。

## 共享交付契约

- 先区分事实、判断、未知和待核验项。
- 公开素材必须具备自有、授权或明确可用的权利依据。
- 每个平台保留独立标题、正文、媒体顺序、标签、声明和发布状态。
- “生成完成”“已存草稿”“已公开发布”是三个不同状态，必须分别提供证据。
- 登录、上传和预览不等于公开发布；最终提交前必须取得针对目标账号和内容的明确授权。
- 遇到验证码、MFA、安全警告、账号不符、声明含义不清或上传状态不明时停止。

详细能力边界与目录说明见 [references/capability-map.md](references/capability-map.md)。
