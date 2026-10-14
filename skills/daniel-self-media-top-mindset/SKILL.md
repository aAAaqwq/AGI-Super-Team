---
name: daniel-self-media-top-mindset
description: 将 Daniel 的利他、真实藏露、情绪纪律、需求聚焦与商业闭环心法应用到自媒体决策。凡涉及 Daniel 个人 IP 的定位、选题、写稿、脚本、封面、跨平台改编、发布规划、增长、变现或复盘时必须先使用；不用于保证爆款、虚构经历、泄露隐私或自动发布。
---

# Daniel 自媒体顶尖心法

先读取项目 `01-source-of-truth.md`、`07-boundaries.md` 和 `13-self-media-top-mindset.md`。本 Skill 是所有自媒体任务的前置决策门，不替代写作、平台专项 Skill、事实核查或人工发布批准。

凡进入文章、教程、案例复盘、图文、口播、视频脚本或跨平台改写，再使用项目 `daniel-content-writing-style` Skill。先由它生成平台无关核心草案并获得用户确认，之后才调用平台专业 Subagent。

## 五维前置检查

1. **利他**：写明目标受众、真实场景、具体问题和内容提供的答案、方法、证据、共鸣或行动力量。
2. **真实藏露**：列出可公开事实、所需证据、需要脱敏的信息和禁止公开内容；目标、推断与情绪不得伪装成事实。
3. **情绪纪律**：区分有效反馈与毁誉噪声；不因恶评报复、不因赞美夸大、不因同行数据临时改主线。
4. **需求聚焦**：一条内容只服务一个核心需求、一个主张和一个可证伪假设；先低成本试错，再放大真实信号。
5. **商业闭环**：标注发现、信任、搜索、转化或复购阶段，以及离用户价值、机会或收入最近的下一动作。

## 工作流

1. 建立 `FACT / INFERENCE / JUDGMENT / UNKNOWN` 清单；关键数字、成果和第一人称经历必须可定位到证据。
2. 输出五维检查结果。任一维缺关键输入时先提问或标记 `BLOCKED`，不得直接批量生产。
3. 选择一个内容命题：`谁 + 在什么场景 + 遇到什么冲突 + Daniel 用什么真实证据提供何种价值`。
4. 确定藏露边界：充分露出方法、作品、过程和正向价值；隐藏不必要的精确收入、家庭隐私、第三方资料、登录态和未落地计划。
5. 生成或审查内容时保留真实矛盾、一个核心观点、可验证过程、限制和下一步，不卖惨、不装导师、不模仿他人身份；具体写作服从 `daniel-content-writing-style`。
6. 设定本轮唯一实验变量及观察指标；粉丝和播放量不得替代信任、有效机会、用户价值或真实收入。
7. 发布前执行五问；真实账号、草稿、发布、互动、投放和外联必须另获人类明确批准。
8. 复盘时分开记录平台事实、可信反馈、个人情绪、商业结果和下一轮假设。

## 输出合同

```yaml
audience_and_need: string
value_delivered: answer|method|evidence|empathy|motivation
facts_and_evidence: []
inferences_and_unknowns: []
expose: []
protect_or_redact: []
single_claim: string
single_experiment: string
funnel_stage: discovery|trust|search|conversion|retention
nearest_business_action: string
emotional_noise_to_ignore: []
decision: PASS|REVISE|BLOCK
human_approval_required: []
```

## 硬门

- 不能说明“对谁有什么用”：`REVISE`。
- 经历、数字、结果无证据，或把目标写成成绩：`BLOCK`。
- 泄露雇主、客户、家人、账户或阴面底牌且无必要受众价值：`BLOCK`。
- 依赖卖惨、阶层恐惧、暴富承诺、刷量或伪造互动：`BLOCK`。
- 同时验证多个核心变量，或只有流量目标没有学习问题：`REVISE`。
- 商业化损害事实、信任、交付或合规：`BLOCK`。

## 完成标准

内容对明确受众有用，核心表达真实，藏露边界清楚，实验可复盘，并推动一个可验证的信任、机会或商业里程碑。任何结果都不得表述为“保证爆火”。
