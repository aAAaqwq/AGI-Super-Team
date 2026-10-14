# 画质增强

## 能力用途

用于视频画质增强。利用 AI 算法对输入视频进行分析，并智能执行包括但不限于视频去噪、色彩增强、清晰度提升、瑕疵修复和超分辨率的一系列优化操作。提供 standard 和 professional 两种版本：standard 兼顾处理速度与视频画质，内置高频使用的 10 余种增强算法，适用于视频分发场景的画质增强；professional 提供极致画质增强，内置 30 余种深度 AI 增强算法，适用于影视级视频制作。不同版本会影响增强算法的强度、适用场景与计费。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video enhance-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `bit_depth` | `--bit-depth` | integer | 否 | 8 | 枚举: [8,10,12] | 目标色深，也称为位深。bit_depth 仅在 professional 版本支持设置，可选 8、10、12，默认 8。8 表示 8 bit 位深，使用 H.264 编码；10 表示 10 bit 位深，使用 H.265 编码；12 表示 12 bit 位深，使用 H.265 编码。 |
| `bitrate_level` | `--bitrate-level` | string | 否 | "medium" | 枚举: ["low","medium","high"] | 用于控制输出视频的平均码率，会影响视频的视觉质量和最终的文件体积。可选 low、medium、high；其中 high 表示高码率，medium 表示中码率，推荐使用，low 表示低码率；默认 medium。 |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `fps` | `--fps` | number | 否 | - | 最小值: 15；最大值: 120 | 目标帧率，单位为 fps，取值范围为 15 到 120。若未指定 fps，输出视频将保持与原始片源一致的帧率。建议 fps 不超过原片的 4 倍。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `resolution` | `--resolution` | string | 否 | - | 枚举: ["240p","360p","480p","540p","720p","1080p","2k","4k","8k"] | 目标分辨率档位，支持 240p、360p、480p、540p、720p、1080p、2k、4k、8k。可以使用 resolution 将视频超分到指定规格。resolution 与 resolution_limit 不可同时配置。 |
| `resolution_limit` | `--resolution-limit` | integer | 否 | - | 最小值: 128；最大值: 4320 | 目标分辨率的短边像素限制，取值范围为 128 到 4320。系统将根据 resolution_limit 在保持原视频宽高比的前提下等比缩放到该限制值。resolution_limit 与 resolution 不可同时配置。 |
| `scene` | `--scene` | string | 否 | "common" | 枚举: ["common","ugc","short_series","aigc","old_film"] | 用于选择一个针对特定业务场景的预设画质增强模板。scene 仅在 tool_version 为 standard 时生效，可选 common、ugc、short_series、aigc、old_film，默认 common。其中 common 表示通用模板，ugc 表示 UGC 短视频场景，short_series 表示短剧场景，aigc 表示 AIGC 内容场景，old_film 表示老片修复场景。 |
| `tool_version` | `--tool-version` | string | 否 | "standard" | 枚举: ["standard","professional"] | 影响增强算法的强度、适用场景与计费。可选 standard 和 professional，默认 standard。其中 standard 表示标准版，兼顾处理速度与视频画质，内置高频使用的 10 余种增强算法，覆盖主流播放平台画质要求，适用于视频分发场景的画质增强；professional 表示专业版，提供极致画质增强，保障镜头级画质效果，内置 30 余种深度 AI 增强算法，适用于影视级视频制作。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待增强的视频 URL，支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播的 vod://、火山引擎对象存储的 tos:// 输入协议。支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。建议单个输入文件大小不超过 10 GB。输入视频分辨率最高支持 2K，长边范围为 360 到 2560，短边范围为 360 到 1440。 |

### 调用示例

```bash
mediakit-cli video enhance-video \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 输出视频的总时长，单位为秒。 |
| `result.fps` | number | 否 | Cloud 终态 | 输出视频的帧率。 |
| `result.resolution` | string | 否 | Cloud 终态 | 输出视频的分辨率。 |
| `result.tool_version` | string | 否 | Cloud 终态 | 任务实际使用的工具版本。 |
| `result.video_url` | string | 否 | Cloud 终态 | 增强后的视频文件下载地址。未设置 media_output_destination 时，返回一个 HTTPS 临时下载链接，有效期为 24 小时；设置 media_output_destination 后，返回存储地址，格式为 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key>。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果。本能力耗时常超过单次 query-task 的 9 分钟轮询上限（尤其 `--tool-version professional` 或 `--resolution 4k`/`8k`）；若返回 `status: running` 且命令正常退出，属预期行为，用同一 `task_id` 继续 `--poll-complete`，不要当作状态异常。

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video enhance-video --help
mediakit-cli video enhance-video --schema
```
