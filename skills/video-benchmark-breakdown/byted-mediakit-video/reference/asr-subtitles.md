# 语音转字幕（ASR)

## 能力用途

从视频或音频的语音中识别并提取带时间戳的字幕文本；适用于提取视频字幕、语音转字幕、听写对白等诉求。识别对象是音轨中的语音内容，不是画面上已烧录的硬字幕。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video asr-subtitles`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-confidence`、`--enable-speaker-info`）只能写成 `--enable-confidence=true` 或 `--enable-confidence=false`，也可用裸 `--enable-confidence`（等价 true）；禁止空格传值 `--enable-confidence true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli video asr-subtitles
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio_url` | `--audio-url` | string | 否 | - | - | audio_url 是待处理的音频 URL；支持 mp3、m4a、wav 等主流音频格式；音频文件时长必须不超过 3 小时；支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议。 |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `content_type` | `--content-type` | string | 否 | - | 枚举: ["speech","singing"] | content_type 指定识别内容类型；支持 speech 表示普通说话，singing 表示唱歌；content_type 留空时由算法自动探测识别内容类型。 |
| `enable_confidence` | `--enable-confidence` | boolean | 否 | false | - | enable_confidence 控制是否返回每个字幕片段的置信度，默认为 false；开启 enable_confidence 后，结果中包含 confidence 字段。 |
| `enable_speaker_info` | `--enable-speaker-info` | boolean | 否 | false | - | enable_speaker_info 控制是否开启说话人识别，默认为 false；开启 enable_speaker_info 后，结果中包含 speaker 字段。 |
| `language` | `--language` | string | 否 | - | 枚举: ["cmn-Hans-CN","eng-US"] | language 指定识别语种；支持 cmn-Hans-CN 表示简体中文，eng-US 表示英语；language 留空时由算法自动探测语种。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 否 | - | - | video_url 是待处理的视频 URL；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；视频文件时长必须不超过 3 小时；支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议；video_url 和 audio_url 同时存在时优先使用 video_url。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | duration 是输入音频或视频的总时长，单位为秒。 |
| `result.subtitles` | array<object> | 否 | Cloud 终态 | subtitles 是字幕片段列表，每个元素包含字幕文本和时间戳。 |
| `result.subtitles[].confidence` | number | 否 | Cloud 终态 | confidence 是字幕片段的置信度得分，必须不小于 0 且不大于 1，仅在请求中的 enable_confidence 为 true 时返回。 |
| `result.subtitles[].end_time` | number | 否 | Cloud 终态 | end_time 是字幕片段的结束时间，单位为秒。 |
| `result.subtitles[].speaker` | string | 否 | Cloud 终态 | speaker 是说话人标识，仅在请求中的 enable_speaker_info 为 true 时返回。 |
| `result.subtitles[].start_time` | number | 否 | Cloud 终态 | start_time 是字幕片段的起始时间，单位为秒。 |
| `result.subtitles[].subtitle_text` | string | 否 | Cloud 终态 | subtitle_text 是识别出的字幕文本。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video asr-subtitles --help
mediakit-cli video asr-subtitles --schema
```
