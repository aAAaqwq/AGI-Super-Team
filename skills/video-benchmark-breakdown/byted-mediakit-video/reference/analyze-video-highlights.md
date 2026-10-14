# 高光片段提取

## 能力用途

支持短剧 Miniseries 和小游戏 Game 两种分析模型，用于高光片段提取，并输出精准时间戳、高光打分、OCR 文本和画面描述，供二次开发或内容分析。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video analyze-video-highlights`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--minigame-info`）需传合法 JSON 字符串并整体加单引号，例如 `--minigame-info '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video analyze-video-highlights \
  --video-urls "url1,url2"
  --model <model> \
  --mode <mode>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数；任务完成时会通过事件回调原样返回，用于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址；提供后优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 默认不传。用户明确指定时原样使用；用户明确要求重试时，同一逻辑请求的重试链必须复用同一 token。已有 token 时必须复用原值；此前请求未带 token 时，可从本次重试开始创建一次并持续复用，但该 token 不对此前请求提供追溯幂等。业务参数变化视为新请求，不得复用旧 token。不得为每次尝试生成不同值。CLI/MCP runtime 不判断重试意图，也不自动生成 token。 |
| `minigame_info` | `--minigame-info` | object | 否 | - | - | 仅当 model 为 Game 时可选填，用于提供小游戏描述信息以辅助模型更精准地识别高光内容。 |
| `minigame_info.highlight_definition` | - | string | 否 | - | 最长长度: 5000 | 描述游戏中的高光时刻或精彩瞬间的定义。 |
| `minigame_info.name` | - | string | 否 | - | 最长长度: 5000 | 用于标识游戏内容的游戏名称。 |
| `minigame_info.play_definition` | - | string | 否 | - | 最长长度: 5000 | 描述游戏的玩法规则或核心特点。 |
| `mode` | `--mode` | string | 是 | - | 枚举: ["StorylineCuts","HighlightExtract"] | 当 model 为 Miniseries 时，mode 必须为 StorylineCuts；当 model 为 Game 时，mode 必须为 HighlightExtract。 |
| `model` | `--model` | string | 是 | - | 枚举: ["Miniseries","Game"] | Miniseries 是短剧模型，结合故事线理解，智能识别钩子点、反转、亲密、冲突等高光片段；Game 是小游戏模型，精准识别玩法操作片段和击杀、连胜、满血反杀等高光瞬间。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID；不传时默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以按队列对应的项目进行分账。队列可创建和管理，系统会自动分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 100 | 待分析的视频 URL 列表，不同模型对输入视频的数量、时长和内容有不同要求。支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入分辨率最高支持 1080p。用于短剧高光片段提取时，单次任务最多支持输入 30 个视频文件，累计总时长建议不超过 45 分钟，输入素材必须同时包含视频流和音频流，视频画面下半部分垂直位置 0.5-1.0 范围内必须包含清晰居中的中文字幕，音频轨道必须包含清晰可识别的中文对话文本；仅含 BGM（含歌词）、纯音乐、语气词或无有效语义的声音将无法准确识别剧情逻辑。用于小游戏高光片段提取时，当前单次任务仅支持输入单个视频文件；输入多个视频时默认选择第一个文件分析，输入文件时长不得超过 10 分钟。 CLI 传参时可使用逗号分隔多个值，或重复传递该 flag；不要传 JSON 数组字符串。 |

### 任务结果查询

提交成功后会返回 `task_id`，再执行 `mediakit-cli shared query-task --task-id <task_id>` 查询。

- 当前命令：`mediakit-cli video analyze-video-highlights`
- 推荐查询：`mediakit-cli shared query-task --task-id <task_id>`

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video analyze-video-highlights --help
mediakit-cli video analyze-video-highlights --schema
```
