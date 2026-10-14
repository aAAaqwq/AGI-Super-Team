# 视频理解智能策略

## 能力用途

基于视觉大模型，对输入的视频 URL 列表进行通用视频内容分析，输出视频级别的结构化理解结果，适用于内容审核、视频检索、标签生成等场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video video-understand-router`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 数组参数（`--prefer-endpoints`、`--prefer-models`、`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--prefer-endpoints "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--manual-option`）需传合法 JSON 字符串并整体加单引号，例如 `--manual-option '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video video-understand-router \
  --video-urls <video_urls_1>,<video_urls_2> \
  --prompt <prompt>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数；任务完成时会通过事件回调原样返回，用于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址；提供后优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 默认不传。用户明确指定时原样使用；用户明确要求重试时，同一逻辑请求的重试链必须复用同一 token。已有 token 时必须复用原值；此前请求未带 token 时，可从本次重试开始创建一次并持续复用，但该 token 不对此前请求提供追溯幂等。业务参数变化视为新请求，不得复用旧 token。不得为每次尝试生成不同值。CLI/MCP runtime 不判断重试意图，也不自动生成 token。 |
| `level` | `--level` | string | 否 | "Economy" | 枚举: ["Economy","Balanced","Quality"] | level 是分析档位，决定任务的默认抽帧策略与模型选择，以在成本、速度和质量之间取得平衡；支持 Economy、Balanced、Quality，默认 Economy。Economy 是速度优先的经济档位，适合大批量、对结果详细程度要求较低的内容标注；Balanced 是速度与质量兼顾的均衡档位，适合常规内容审核与检索场景；Quality 是结果优先的质量档位，适合需要更精细语义理解的场景。 |
| `manual_option` | `--manual-option` | object | 否 | - | - | manual_option 是手动模式相关参数；未传 manual_option 时表示完全使用 level 档位策略，不进行手动覆盖。 |
| `manual_option.fps` | - | number | 否 | 1 | 最小值: 0.2；最大值: 5 | manual_option.fps 是抽帧帧率，设置后会按照指定帧率进行均匀抽帧；最小 0.2，最大 5.0，默认 1.0。 |
| `manual_option.max_snapshot_number` | - | integer | 否 | 0 | 最大值: 1000 | manual_option.max_snapshot_number 是最大抽帧帧数，最小 0，最大 1000，默认 0；显式设置时会覆盖档位策略；设为 0 时由 level 档位决定截图数量。 |
| `manual_option.need_audio` | - | boolean | 否 | false | - | manual_option.need_audio 表示是否开启或关闭音频分析，支持 true 和 false，默认 false。为 true 时开启音频分析，系统将选用支持音视频多模态的模型，并分析音频内容。为 false 时关闭音频分析，仅分析视频画面；即使 manual_option.need_audio 为 false 或未提供，如果 prompt 中包含“声音”、“音乐”等音频相关关键词，也可能自动触发音频分析。 |
| `prefer_endpoints` | `--prefer-endpoints` | array<string> | 否 | - | 最少项数: 1；最多项数: 10 | prefer_endpoints 是优先使用的推理接入点 ID（Endpoint ID）列表，最多 10 个；系统将从 prefer_endpoints 指定的推理接入点中结合策略选择最终模型；prefer_endpoints 的优先级高于 prefer_models。 CLI 传参时可使用逗号分隔多个值，或重复传递该 flag；不要传 JSON 数组字符串。 |
| `prefer_models` | `--prefer-models` | array<string> | 否 | - | 最少项数: 1；最多项数: 10 | prefer_models 是优先使用的模型 ID（Model ID）列表，最多 10 个；系统将从 prefer_models 指定的模型中结合策略选择最终模型。 CLI 传参时可使用逗号分隔多个值，或重复传递该 flag；不要传 JSON 数组字符串。 |
| `prompt` | `--prompt` | string | 是 | - | 最短长度: 1 | prompt 是用于指导大模型对视频内容进行分析的自然语言描述，最小长度为 1。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID；不传时默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以按队列对应的项目进行分账。队列可创建和管理，系统会自动分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `scene` | `--scene` | string | 否 | - | 枚举: ["editing"] | scene 是分析场景，用于系统优化处理策略；指定 scene 后，系统会自动决策使用该场景的最佳策略；不传时表示通用场景。editing 表示创作剪辑场景，模型会侧重于理解并输出带有精确时间戳的详细分镜信息，适用于分镜理解、智能剪辑、二次 AIGC 创作等下游任务。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 10 | video_urls 是待处理的视频 URL 列表，支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；单次任务最多支持传入 10 个视频文件。 CLI 传参时可使用逗号分隔多个值，或重复传递该 flag；不要传 JSON 数组字符串。 |

### 任务结果查询

提交成功后会返回 `task_id`，再执行 `mediakit-cli shared query-task --task-id <task_id>` 查询。

- 当前命令：`mediakit-cli video video-understand-router`
- 推荐查询：`mediakit-cli shared query-task --task-id <task_id>`

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video video-understand-router --help
mediakit-cli video video-understand-router --schema
```
