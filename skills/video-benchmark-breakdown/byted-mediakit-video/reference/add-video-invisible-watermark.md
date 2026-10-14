# 添加视频暗水印

## 能力用途

用于视频暗水印添加。在不影响视频画面视觉质量与完整性的前提下，将一串数字信息隐藏式地嵌入视频文件中。适用于视频版权保护、内容泄露溯源、文件真实性校验等场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video add-video-invisible-watermark`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待添加暗水印的视频 URL。支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式；支持公网 HTTP/HTTPS URL、本地文件路径、视频点播 vod://、对象存储 tos:// 四种输入协议；分辨率最高支持 4K。 |
| `watermark_content` | `--watermark-content` | string | 是 | - | 格式: "^[1-9][0-9]{0,18}$" | 待嵌入视频的隐藏数字信息，用于版权追溯。需传入一个代表 64 位正整数的字符串，且必须为纯数字字符串；数字必须在 1 至 9223372036854775807 之间；不允许使用前导零或包含任何非数字字符。 |
| `watermark_level` | `--watermark-level` | string | 否 | "normal" | 枚举: ["low","normal","high"] | 可选的暗水印强度，用于决定抗攻击性与画面影响程度的平衡。normal 为标准强度，在画质与抗攻击性之间取得平衡，适用于大多数场景；high 为高强度，抗攻击性最强，能抵抗更强的视频处理，但对画面的潜在影响也相对更大；默认值为 normal 标准强度。 |

### 调用示例

```bash
mediakit-cli video add-video-invisible-watermark \
  --video-url <video_url> \
  --watermark-content <watermark_content>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 输入视频的总时长，单位为秒，用于计量计费。 |
| `result.resolution` | string | 否 | Cloud 终态 | 输入视频的分辨率。 |
| `result.video_url` | string | 否 | Cloud 终态 | 已嵌入暗水印的视频文件地址。设置 media_output_destination 后，返回存储地址，格式为 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key>；未设置 media_output_destination 时，返回 HTTPS 临时下载链接，有效期为 24 小时。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video add-video-invisible-watermark --help
mediakit-cli video add-video-invisible-watermark --schema
```
