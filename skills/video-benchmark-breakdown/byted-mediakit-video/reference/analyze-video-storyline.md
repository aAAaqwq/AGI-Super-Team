# 剧情故事线分析

## 能力用途

用于剧情故事线分析，基于大模型视频理解分析单个或多个长视频并生成结构化剧情数据。分析结果包含两部分：按时间顺序排列的剧情片段，以及基于视频片段整理和归纳出的高光故事线。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video analyze-video-storyline`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-snapshot`）只能写成 `--enable-snapshot=true` 或 `--enable-snapshot=false`，也可用裸 `--enable-snapshot`（等价 true）；禁止空格传值 `--enable-snapshot true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。

### 调用示例

```bash
mediakit-cli video analyze-video-storyline \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `enable_snapshot` | `--enable-snapshot` | boolean | 否 | false | - | enable_snapshot 可选，用于控制是否为每个剧情片段生成关键帧快照；默认 false。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 30 | video_urls 是待处理的视频 URL 列表，支持公网 HTTP/HTTPS URL、本地文件路径、vod:// 和 tos:// 四种协议来源，支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；单次任务最多支持传入 30 个视频文件；输入视频分辨率最高支持 1080p；输入视频累计总时长不得超过 210 分钟，即 3.5 小时；建议单个视频文件时长不得超过 150 分钟，即 2.5 小时。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | duration 表示输入视频的总时长，单位为秒。 |
| `result.source_video_info` | array<object> | 否 | Cloud 终态 | source_video_info 是输入源视频的分析结果列表，包含原始 URL、AI 生成的标题和简介等信息；支持通过 storyline_clips 标注的源视频索引追溯每个片段对应的输入文件。 |
| `result.source_video_info[].source_video_index` | integer | 否 | Cloud 终态 | source_video_index 是从 0 开始的片源索引。 |
| `result.source_video_info[].source_video_summary` | string | 否 | Cloud 终态 | source_video_summary 是视频简介。 |
| `result.source_video_info[].source_video_tag` | array<string> | 否 | Cloud 终态 | source_video_tag 是视频标签列表。 |
| `result.source_video_info[].source_video_title` | string | 否 | Cloud 终态 | source_video_title 是视频标题。 |
| `result.source_video_info[].source_video_url` | string | 否 | Cloud 终态 | source_video_url 是片源的原始 URL。 |
| `result.storyline_clips` | array<object> | 否 | Cloud 终态 | storyline_clips 是 AI 将一个或多个长视频的故事按剧情发展智能切分并按时间顺序排列得到的基础视频片段数组；storyline_clips 是最基础、最详细的分析结果，每个片段包含标题、简介、源视频起止时间和精彩度评分。 |
| `result.storyline_clips[].clip_dialogue` | string | 否 | Cloud 终态 | clip_dialogue 是视频片段内的主要对话文本。 |
| `result.storyline_clips[].clip_end_time` | number | 否 | Cloud 终态 | clip_end_time 是视频片段在源视频中的结束时间，单位为秒。 |
| `result.storyline_clips[].clip_index` | integer | 否 | Cloud 终态 | clip_index 是从 0 开始的视频片段唯一索引。 |
| `result.storyline_clips[].clip_score` | number | 否 | Cloud 终态 | clip_score 是高光打分，分数越高表示越精彩；范围必须为 1 到 5。 |
| `result.storyline_clips[].clip_snapshot_url` | string | 否 | Cloud 终态 | clip_snapshot_url 是关键帧快照 URL，仅在请求中 enable_snapshot 为 true 时返回；enable_snapshot 开启后，storyline_clips 的每个对象包含 clip_snapshot_url。 |
| `result.storyline_clips[].clip_start_time` | number | 否 | Cloud 终态 | clip_start_time 是视频片段在源视频中的开始时间，单位为秒。 |
| `result.storyline_clips[].clip_summary` | string | 否 | Cloud 终态 | clip_summary 是视频片段简介。 |
| `result.storyline_clips[].clip_title` | string | 否 | Cloud 终态 | clip_title 是视频片段标题。 |
| `result.storyline_clips[].source_video_index` | integer | 否 | Cloud 终态 | source_video_index 标识视频片段来自哪个输入视频，并对应 source_video_info 的片源索引。 |
| `result.storyline_highlights` | array<object> | 否 | Cloud 终态 | storyline_highlights 是基于 storyline_clips 整理和归纳出的故事线数组。 |
| `result.storyline_highlights[].highlight_clips_index` | array<integer> | 否 | Cloud 终态 | highlight_clips_index 是组成该高光故事线的剧情片段索引列表，对应 storyline_clips 中的 clip_index；highlight_clips_index 列表说明一条故事线由哪些剧情片段组成。 |
| `result.storyline_highlights[].highlight_index` | integer | 否 | Cloud 终态 | highlight_index 是从 0 开始的高光故事线唯一索引。 |
| `result.storyline_highlights[].highlight_summary` | string | 否 | Cloud 终态 | highlight_summary 是高光故事线简介。 |
| `result.storyline_highlights[].highlight_title` | string | 否 | Cloud 终态 | highlight_title 是高光故事线标题。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video analyze-video-storyline --help
mediakit-cli video analyze-video-storyline --schema
```
