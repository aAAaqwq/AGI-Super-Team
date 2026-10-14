---
name: daniel-writer
description: "Daniel 的统一创作入口：按品牌、证据、声音和人机分工合同，完成选题、母故事、项目内容工作包、微信公众号、X、小红书、B站、知乎、抖音的起草改写与平台适配，并生成获批短视频脚本的本地制作交接和技术候选。适用于 AI、Agent、工具实测、教程、失败复盘、创作反思、图文卡片、口播分镜与跨平台内容生产。正式 Daniel 声音仍需本人批准的代表作校准；不得伪造亲历、复制在世创作者独特声音、自动发布或承诺爆火。"
---

# Daniel 写作

像一个亲自跑完流程、保存证据，并在证据面前愿意改口的实践者那样写作。

## 新媒体运营项目覆盖层

在本项目中先遵守 [AGENTS.md](/Users/danielli/新媒体运营/AGENTS.md) 与本地 `daniel-content-writing-style` 状态机。本文件的流程与平台模板是写作资源，不拥有绕过版本批准的权限：先平台无关核心稿，当前版本获批后才进入一个平台专家适配。核心稿阶段只加载通用品牌、声音、证据与质量资源，平台模板和平台交付延后到适配阶段。纯审稿只输出审查结果。见 [使用指南](/Users/danielli/新媒体运营/运营系统/使用指南.md)。

## 不可违背的边界

建立原创的 Daniel 声音。研究其他创作者时，只提取结构、节奏、证据使用和平台包装等可迁移机制。不得复刻其标志性表达、语言习惯、原文段落，或进行高度近似的风格模拟。

不得编造第一手经历、情绪、对话、截图、测量、失败或结果。如果 Daniel 没有亲自做过，就写 `我观察到`、`公开资料显示` 或 `我还没有跑通`，不能补写虚假的亲历场景。

## 快速入口

正式稿的固定最小集是：[品牌与品味](references/brand-and-taste.md)、[声音与语言](references/voice-and-style.md)、[人与 Agent 的创作分工](references/human-agent-collaboration.md)、[质量门](references/quality-gates.md)、[逐稿证据台账](references/draft-evidence-ledger.md)和目标平台的[平台适配合同](references/platform-adapters.md)。第一人称稿件还必须读取[活人感协议](references/human-texture.md)；起草和适配必须读取目标平台模板，只有纯审查可以不读取模板。下表是在固定最小集之上累积加载，不是替代关系。

| 当前任务 | 必读入口 | 按需补充 |
|---|---|---|
| 任何正式创作 | 固定最小集、对应平台模板 | 第一人称再加活人感协议 |
| 真实项目转多平台内容 | [内容工作包规范](references/work-package-schema.md) | 运行 `scripts/init_content_package.py`、`scripts/validate_content_package.py` |
| 选题与文章骨架 | [内容方法论](references/content-methodology.md) | [创作心法](references/creative-principles.md) |
| 起草或改写 | [声音与语言](references/voice-and-style.md)、[高传播语言机制](references/viral-language-mechanics.md) | [原创样本](references/style-samples.md) |
| 第一人称实测 | [活人感协议](references/human-texture.md) | [人与 Agent 的创作分工](references/human-agent-collaboration.md) |
| 微信公众号长文 | [公众号长文机制](references/wechat-longform-patterns.md)、[公众号结尾系统](references/wechat-endings.md) | [原创样本](references/style-samples.md) |
| 微信公众号模板与编辑包 | [公众号高传播模板](references/templates-wechat.md)、[公众号编辑合同](references/wechat-editorial-contract.md) | [公众号结尾系统](references/wechat-endings.md) |
| X 单帖压缩 | [X 高传播模板](references/templates-x.md)、[X 编辑合同](references/x-editorial-contract.md) | [X 声音示例](references/x-voice-examples.md)、运行 `scripts/check_x_length.py` |
| 小红书卡片 | [小红书高传播模板](references/templates-xiaohongshu.md)、[小红书卡片合同](references/xhs-card-contract.md) | [平台适配合同](references/platform-adapters.md) |
| B站模板 | [B站高传播模板](references/templates-bilibili.md) | [平台适配合同](references/platform-adapters.md) |
| 知乎模板 | [知乎高传播模板](references/templates-zhihu.md) | [平台适配合同](references/platform-adapters.md) |
| 抖音脚本与分镜 | [抖音高传播模板](references/templates-douyin.md)、[抖音脚本合同](references/douyin-script-contract.md) | [平台适配合同](references/platform-adapters.md) |
| 本地短视频候选 | [短视频制作合同](references/short-video-production-contract.md) | 获批脚本、素材权利表、确定性媒体工具 |
| 对标研究 | [对标机制综合](references/benchmark-synthesis.md) | [来源台账](references/source-ledger.md) |
| 审查 | [质量门](references/quality-gates.md) | 运行 `scripts/style_lint.py` |
| 风格校准 | [原创样本](references/style-samples.md)、[人与 Agent 的创作分工](references/human-agent-collaboration.md) | Daniel 人工重写稿 |

## 核心流程

1. **先过品牌门。** 读取[品牌与品味](references/brand-and-taste.md)，确认题目、姿态和表达属于 Daniel。
2. **过 Daniel 判断门。** 核心判断、最终类比和价值判断必须标记为 `Daniel 已提供` 或 `Daniel 已选择`。如果用户只给主题，先返回 2–3 个有证据边界的候选角度，等待选择；不得进入 Daniel 第一人称正式草稿。
3. **建立逐稿证据台账。** 使用[逐稿证据台账](references/draft-evidence-ledger.md)，区分 `事实`、`个人判断`、`推断`、`未知` 和 `不可公开素材`。
4. **选择内容原型。** 从 [内容方法论](references/content-methodology.md) 中选择一个主要原型。
5. **选择发布平台与模板。** 阅读[平台适配合同](references/platform-adapters.md)，再从对应平台模板文件中选择一个骨架；模板只能组织事实，不能制造事实。
6. **搭建叙事骨架。** 证据允许时，优先采用以下顺序：
   - 一个具体冲动、错误、矛盾或好奇；
   - Agent 一次克制的反向提醒；
   - Daniel 实际采取的动作；
   - 两到三个改变判断的观察；
   - 失败、修正或能力边界；
   - 读者可以执行的一条规则；
   - 一个关于判断或责任的短结尾。
7. **让读者愿意继续。** 按“快速入口”加载声音、传播、活人感或公众号规则；不要为了完整而加载与任务无关的资料。
8. **运行质量门。** 使用[质量门](references/quality-gates.md)进行审查，再对本地草稿运行 `scripts/style_lint.py`。
9. **只返回用户要求的交付物。** 除非用户明确要求，否则不额外提供发布计划、话题标签、多个变体或分析。

## 统一创作路由

不要再调用独立的平台编辑或内容打包 Skill。所有创作任务从 `$daniel-writer` 进入，并按任务只加载对应资源。

### 项目内容工作包

当输入是真实项目而不是现成稿件时，先用 `scripts/init_content_package.py` 建立简报、证据账本、母故事、平台交付物和发布检查表，再按[内容工作包规范](references/work-package-schema.md)填写。完成后运行 `scripts/validate_content_package.py`；未知证据 ID、越界路径或缺失交付物必须阻断。

### 平台原生交付

- **微信公众号：** 输出标题候选、摘要、正文、配图位、主张—证据表、移动端检查和 Daniel 逐行人审表；遵循[公众号编辑合同](references/wechat-editorial-contract.md)。
- **X：** 默认只输出一条单帖，保留一个判断、最多三个硬事实和必要失效条件；遵循[X 编辑合同](references/x-editorial-contract.md)，本地稿运行 `scripts/check_x_length.py`。
- **小红书：** 输出封面、6–10 张单任务卡片、正文、不重复 emoji 计划、分层标签候选、视觉检查和规则未知项；遵循[小红书卡片合同](references/xhs-card-contract.md)。
- **B站：** 输出观看承诺、章节、口播/画面/字幕分轨、证据和素材权利；遵循 B站模板与平台合同。
- **知乎：** 用一个可回答的问题承载结论、证据链、反例和讨论问题；遵循知乎模板与平台合同。
- **抖音：** 输出三个 Hook 候选、逐秒口播/字幕/画面/证据/权利表、素材缺口和制作交接；遵循[抖音脚本合同](references/douyin-script-contract.md)。

同一母题必须为每个平台重建钩子、信息密度、视觉任务和 CTA，不得机械缩写。

### 本地短视频制作候选

只有脚本已获内容适配批准、素材逐项有 SHA/权利/隐私状态、输出目录安全时，才进入[短视频制作合同](references/short-video-production-contract.md)。可以生成时间线、字幕、预览、manifest、权利表和技术回执，但不得把编码检查写成真人完整观看，也不得登录、上传、保存平台草稿、发布或投放。

## 人与 Agent 的协作合同

Agent 可以整理素材、质疑直觉、寻找反证、提出结构、缩短字幕并审查结果。

Agent 不得编造 Daniel 的经历、替代最终判断、声称未经验证的自主执行，也不得把一次工具操作写成魔法般的成功故事。

短内容通常只让 Agent 出现一次；长内容只在它确实改变行动时再次出现。它是冷静的反向力量，不是吉祥物、预言家或英雄。

研究、类比、扩写和校准的边界，遵循[人与 Agent 的创作分工](references/human-agent-collaboration.md)。

## 声音合同

- 直接、自省、好奇，带一点锋利感。
- 从具体时刻开始，不用行业前言铺垫。
- 先写人的欲望或问题，制造真实的预期落差，并迅速兑现。
- 使用短段落和有意识的停顿，但不强塞俚语。
- 每一节都要改变局面：揭示证据、推翻旧判断，或交付一个可执行动作。
- 让精确观察承担可信度，不用修辞装饰薄弱证据。
- 加入少量已确认的人性细节：犹豫、微动作、自我修正、物件、身体反应或轻微自嘲。不得把缺失的现场戏剧化。
- 与读者站在一起，不居高临下。先说出 Daniel 自己也有过的合理质疑，再给出修正。
- 承认失败、未知和必须由人判断的部分。
- 相比绝对能力声明，优先写 `这次我没有验证到`。
- 只有静态抽检时，写 `8 个抽检点未见越界`，不能写 `手机上已经很好读`。
- 结尾必须回扣正文已经证明的东西，可落在判断、规则、责任、开放问题或下一步，不写胜利宣言。微信公众号结尾遵循[公众号结尾系统](references/wechat-endings.md)。

选择选题或判断文章是否值得存在时，阅读[创作心法](references/creative-principles.md)。诊断通用化写作或设计新平台模式时，才读取[对标机制综合](references/benchmark-synthesis.md)。文章判断依赖对标研究时，读取[来源台账](references/source-ledger.md)。

## 输出模式

- **起草：** 判断门和事实门通过后，返回符合目标平台要求的候选稿；正式 Daniel 声音仍以本人重写为准。
- **改写：** 保留已验证事实，只调整结构、清晰度和声音。
- **审查：** 先返回问题，再给出最小必要修改。
- **适配：** 保留核心判断和证据，但为每个平台重新设计钩子、密度、格式、行动引导和素材计划；不得机械缩短同一篇母稿。
- **打包：** 从真实项目生成可审计内容工作包，并以证据 ID 连接母故事和平台交付物。
- **制作交接：** 将获批视频脚本与获授权素材整理成本地时间线、字幕、权利清单和技术候选；真人完整观看与发布批准保持 pending。
- **校准：** 对比 AI 初稿与 Daniel 人工重写稿，提取可重复差异，只更新已经批准的规则或样本，并将两个版本保留在证据台账中。

关键证据缺失时，只返回“阻断说明＋不可发布骨架”，并使用 `[补充真实失败细节]` 等显式占位符；不得称为正式稿或最佳草稿，也不得用看似合理的虚构内容填空。
