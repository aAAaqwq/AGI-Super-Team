# 精细化字幕擦除

## 能力用途

用于字幕擦除（精细化版），对视频字幕进行高质量无痕擦除，并最大程度还原视频画面。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video erase-video-subtitle-pro`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 对象或对象数组参数（`--erase-ratio-location`、`--subtitle-filter`、`--time-segment-filter`）需传合法 JSON 字符串并整体加单引号，例如 `--erase-ratio-location '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video erase-video-subtitle-pro \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `erase_ratio_location` | `--erase-ratio-location` | array<object> | 否 | - | 最少项数: 0；最多项数: 20 | 配置擦除框位置数组后，系统仅在指定矩形框选区域内执行文本擦除。每个 location 由左上角与右下角两个顶点确定矩形擦除区域，坐标以画面左上角 (0, 0) 为原点、右下角为 (1, 1)，X 轴向右、Y 轴向下，使用相对画面宽高的归一化比例 [0,1]。最多支持 20 个擦除框。 |
| `erase_ratio_location[].bottom_right_x` | - | number | 是 | - | 最小值: 0；最大值: 1 | bottom_right_x 是框选区域右下角相对于视频左上角在 X 轴上的偏移比例，范围 [0,1]；0 与左边缘对齐，1 与右边缘对齐。 |
| `erase_ratio_location[].bottom_right_y` | - | number | 是 | - | 最小值: 0；最大值: 1 | bottom_right_y 是框选区域右下角相对于视频左上角在 Y 轴上的偏移比例，范围 [0,1]；0 与上边缘对齐，1 与下边缘对齐。 |
| `erase_ratio_location[].top_left_x` | - | number | 是 | - | 最小值: 0；最大值: 1 | top_left_x 是框选区域左上角相对于视频左上角在 X 轴上的偏移比例，范围 [0,1]；0 与左边缘对齐，1 与右边缘对齐。 |
| `erase_ratio_location[].top_left_y` | - | number | 是 | - | 最小值: 0；最大值: 1 | top_left_y 是框选区域左上角相对于视频左上角在 Y 轴上的偏移比例，范围 [0,1]；0 与上边缘对齐，1 与下边缘对齐。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `mode` | `--mode` | string | 否 | "Subtitle" | 枚举: ["Subtitle","Text"] | 字幕擦除模式，默认 Subtitle，支持 Subtitle 和 Text。Subtitle 模式擦除 OCR 检测为字幕的文本，默认仅处理视频画面下半部分（下方 50%）区域；配置 erase_ratio_location 时，只处理自定义擦除框与画面下半部分的交集。Text 模式擦除 OCR 检测为字幕及人名、地名等其他类型文本，不包含牌匾等场景文字；默认检测整个视频画面，配置 erase_ratio_location 时仅在指定擦除框内执行。 |
| `model_version` | `--model-version` | string | 否 | "v4" | 枚举: ["v4","v5"] | 擦除算法版本，支持 v4 和 v5，默认 v4。相比 V4，V5 优化 AIGC 生成视频擦除字幕后的闪烁问题、带阴影字幕的擦除效果和误擦问题，并提升处理速度。 |
| `output_encode_mode` | `--output-encode-mode` | string | 否 | "Quality" | 枚举: ["Quality","Size"] | 输出视频编码模式，默认 Quality。Quality 采用较高码率编码，画质更好，但文件体积可能更大；Size 在保证一定画质的前提下使输出码率接近源文件。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `subtitle_filter` | `--subtitle-filter` | object | 否 | - | - | subtitle_filter 通过文字高度和水平居中程度帮助系统更准确地判断哪些文本属于字幕，避免误擦大标题、台标、水印等非字幕文本。仅当文本高度不低于下限、不高于上限且水平方向足够居中时，文本才会被判定为字幕并擦除，大标题、台标、水印等文本会被排除。仅在 mode 为 Subtitle 时生效，不传时使用系统默认值。 |
| `subtitle_filter.center_offset_ratio` | - | number | 否 | - | 最小值: 0；最大值: 1 | center_offset_ratio 是文字区域中心相对视频宽度中心的最大偏离比例，范围 [0,1]，默认 0.08；超过该比例的文本不会被判定为字幕。 |
| `subtitle_filter.max_text_height_ratio` | - | number | 否 | - | 最小值: 0；最大值: 1 | max_text_height_ratio 是相对视频高度的文字高度最大比例，范围 [0,1]；高于该高度的文本不会被判定为字幕；不传时 v4 默认 0.2（20%），v5 默认 0.1（10%）。 |
| `subtitle_filter.min_text_height_ratio` | - | number | 否 | - | 最小值: 0；最大值: 1 | min_text_height_ratio 是相对视频高度的文字高度最小比例，范围 [0,1]，默认 0.01（1%）；低于该高度的文本不会被判定为字幕。 |
| `time_segment_filter` | `--time-segment-filter` | object | 否 | - | - | 按 mode 对指定时间段执行或跳过擦除；不配置则对整段视频生效，适用于只擦除正片或保留片头、片尾字幕等场景。 |
| `time_segment_filter.mode` | - | string | 是 | - | 枚举: ["skip","selected"] | skip 跳过 segments 中列出的时间段并擦除其余部分；selected 仅擦除 segments 中列出的时间段。 |
| `time_segment_filter.segments` | - | array<object> | 是 | - | 最少项数: 1 | segments 时间段列表至少包含 1 个时间段。 |
| `time_segment_filter.segments[].end_time` | - | number | 是 | - | 最小值: 0 | end_time 是以秒为单位的片段结束时间，需大于 start_time。 |
| `time_segment_filter.segments[].start_time` | - | number | 是 | - | 最小值: 0 | start_time 是以秒为单位的片段起始时间，取值大于等于 0。 |
| `video_url` | `--video-url` | string | 是 | - | - | 支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议，支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式，输入分辨率最高支持 2K，输出分辨率最高支持 1080P。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | result.duration 表示输出视频总时长，单位为秒。 |
| `result.video_url` | string | 否 | Cloud 终态 | result.video_url 是擦除字幕后的视频地址；未设置 media_output_destination 时返回有效期 24 小时的 HTTPS 临时下载链接，请及时下载保存；设置后返回 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key> 存储地址。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video erase-video-subtitle-pro --help
mediakit-cli video erase-video-subtitle-pro --schema
```
