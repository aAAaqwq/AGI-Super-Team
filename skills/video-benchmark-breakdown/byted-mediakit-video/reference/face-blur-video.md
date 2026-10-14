# 视频人脸打码

## 能力用途

视频人脸打码可自动精准识别视频画面中的人脸区域，并对所有人脸进行模糊或马赛克处理，适用于需要保护人物五官隐私的场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video face-blur-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--upright-face-only`）只能写成 `--upright-face-only=true` 或 `--upright-face-only=false`，也可用裸 `--upright-face-only`（等价 true）；禁止空格传值 `--upright-face-only true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli video face-blur-video \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `face_box_expand` | `--face-box-expand` | number | 否 | 0.2 | 最小值: 0；最大值: 1 | 人脸边界框扩展比例，范围大于 0.0 且不超过 1.0，默认值为 0.2。系统将根据该比例在检测到的人脸区域基础上向外扩展打码范围。 |
| `face_confidence` | `--face-confidence` | number | 否 | 0.35 | 最小值: 0.1；最大值: 1 | 人脸检测置信度阈值，范围 0.1 至 1.0，默认值为 0.35。低于此阈值的检测结果将被丢弃。 |
| `mask_mode` | `--mask-mode` | string | 否 | "mosaic" | 枚举: ["mosaic","blur"] | 人脸打码方式：mosaic 表示马赛克，为默认值；blur 表示高斯模糊。 |
| `mask_strength` | `--mask-strength` | string | 否 | "medium" | 枚举: ["low","medium","high"] | 人脸打码强度：low 表示低强度；medium 表示中强度，为默认值；high 表示高强度。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `upright_face_only` | `--upright-face-only` | boolean | 否 | true | - | 是否只对正向人脸打码。true 仅处理正脸；false 连同侧脸、歪头等非正向人脸也一并打码。不传时默认 true（只处理正向人脸） |
| `video_url` | `--video-url` | string | 是 | - | - | 待打码的视频 URL，支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和对象存储 tos:// 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；分辨率最高支持 4K，推荐使用 1080P 以获得最佳处理效果；帧率需在 25~60 范围内；视频时长不得超过 10 分钟。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 输出视频总时长，单位为秒，可用于计量计费。 |
| `result.video_url` | string | 否 | Cloud 终态 | 已完成人脸打码的视频文件地址。未设置 media_output_destination 时返回 HTTPS 临时下载链接，有效期为 24 小时；设置 media_output_destination 后返回存储地址，格式为 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key>。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video face-blur-video --help
mediakit-cli video face-blur-video --schema
```
