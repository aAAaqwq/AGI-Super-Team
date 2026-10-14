# 视频元信息获取

## 能力用途

探测输入的视频 URL，输出标准化的媒资元信息。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video probe-video-metadata`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待探测的视频 URL。支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。支持公网 HTTP/HTTPS URL、本地上传、火山引擎视频点播和火山引擎对象存储四种输入协议。 |

### 调用示例

```bash
mediakit-cli video probe-video-metadata \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.audio_stream_meta` | object / null | 是 | Cloud 终态 | 主音频流元信息。视频不含音频流时返回 null。 |
| `result.audio_stream_meta.bitrate` | number / null | 否 | Cloud 终态 | 音频流码率，单位为 bps。 |
| `result.audio_stream_meta.channels` | number / null | 否 | Cloud 终态 | 音频声道数。 |
| `result.audio_stream_meta.codec` | string / null | 否 | Cloud 终态 | 音频编码格式，例如 aac。 |
| `result.audio_stream_meta.duration` | number / null | 否 | Cloud 终态 | 音频流时长，单位为秒。 |
| `result.audio_stream_meta.sample_rate` | number / null | 否 | Cloud 终态 | 音频采样率，单位为 Hz。 |
| `result.format_meta` | object / null | 是 | Cloud 终态 | 容器层元信息，包含封装格式、码率、时长、大小等。 |
| `result.format_meta.bitrate` | number / null | 否 | Cloud 终态 | 容器码率，单位为 bps。 |
| `result.format_meta.container` | string / null | 否 | Cloud 终态 | 容器格式（封装格式），例如 MP4。 |
| `result.format_meta.duration` | number / null | 否 | Cloud 终态 | 容器声明的时长，单位为秒。 |
| `result.format_meta.md5` | string / null | 否 | Cloud 终态 | 文件 MD5 值（如可获取）。 |
| `result.format_meta.size` | number / null | 否 | Cloud 终态 | 文件大小，单位为 byte。 |
| `result.video_stream_meta` | object / null | 是 | Cloud 终态 | 主视频流元信息。视频不含视频流时返回 null。 |
| `result.video_stream_meta.bitrate` | number / null | 否 | Cloud 终态 | 视频流码率，单位为 bps。 |
| `result.video_stream_meta.codec` | string / null | 否 | Cloud 终态 | 视频编码格式，例如 h264。 |
| `result.video_stream_meta.duration` | number / null | 否 | Cloud 终态 | 视频流原始时长，单位为秒。 |
| `result.video_stream_meta.dynamic_range` | string / null | 否 | Cloud 终态 | 动态范围，可为 HDR 或 SDR。 |
| `result.video_stream_meta.fps` | number / null | 否 | Cloud 终态 | 视频帧率，单位为 fps。 |
| `result.video_stream_meta.height` | number / null | 否 | Cloud 终态 | 视频流显示高度，单位为像素（px）。 |
| `result.video_stream_meta.width` | number / null | 否 | Cloud 终态 | 视频流显示宽度，单位为像素（px）。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video probe-video-metadata --help
mediakit-cli video probe-video-metadata --schema
```
