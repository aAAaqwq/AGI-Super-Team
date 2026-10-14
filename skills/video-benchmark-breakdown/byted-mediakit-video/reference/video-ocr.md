# 视频识别字幕（OCR）

## 能力用途

用于视频字幕识别（OCR），识别输入视频画面中的字幕信息，输出带时间戳的结构化文本数据。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video video-ocr`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `mode` | `--mode` | string | 否 | "Subtitle" | 枚举: ["Subtitle","Detailed"] | 工作模式。支持 Subtitle 或 Detailed，默认为 Subtitle。Subtitle 模式仅识别视频画面中符合字幕特征的文本，适用于快速提取视频对白、生成字幕稿等场景；Detailed 模式识别画面中更详细的文本信息，包括字幕、水印、台标、标题等；Detailed 模式的返回结果会额外包含 text_label 和 text_location 字段。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待识别的视频 URL。支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入视频分辨率支持 240p 到 4k，单文件视频时长不得超过 10 分钟。 |

### 调用示例

```bash
mediakit-cli video video-ocr \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 输入视频总时长，单位为秒。 |
| `result.subtitles` | array<object> | 否 | Cloud 终态 | 字幕片段列表，每个元素包含字幕文本和时间戳。 |
| `result.subtitles[].end_time` | number | 否 | Cloud 终态 | 结束时间（秒） |
| `result.subtitles[].start_time` | number | 否 | Cloud 终态 | 起始时间（秒） |
| `result.subtitles[].subtitle_text` | string | 否 | Cloud 终态 | 识别文本 |
| `result.subtitles[].text_label` | string | 否 | Cloud 终态 | 文本类别标签（仅 Detailed 模式返回）。Subtitle: 字幕文本；Others: 画面中的其他文字（如水印、台标、贴片等非字幕内容） |
| `result.subtitles[].text_location` | object | 否 | Cloud 终态 | 文本在画面中的像素坐标区域（仅 Detailed 模式返回）。 |
| `result.subtitles[].text_location.bottom_right_x` | integer | 否 | Cloud 终态 | 文本框右下角横坐标，单位 px。 |
| `result.subtitles[].text_location.bottom_right_y` | integer | 否 | Cloud 终态 | 文本框右下角纵坐标，单位 px。 |
| `result.subtitles[].text_location.top_left_x` | integer | 否 | Cloud 终态 | 文本框左上角横坐标，单位 px。 |
| `result.subtitles[].text_location.top_left_y` | integer | 否 | Cloud 终态 | 文本框左上角纵坐标，单位 px。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video video-ocr --help
mediakit-cli video video-ocr --schema
```
