# 智能语义切片

## 能力用途

综合分析视频的画面、语音和叙事结构，通过镜头切换、语音停顿检测等策略，在保证语义完整、避免将单句从中间切断的前提下，将长视频智能地切分为多个独立的素材片段。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video semantic-segment`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `max_duration` | `--max-duration` | number | 否 | 30 | 最小值: 1 | 单个切片的目标最大时长，单位为秒；默认值为 30，最小值为 1。超过该时长的片段将触发强制切分，保证片段不会过长；必须大于或等于 min_duration。 |
| `max_shift_tolerance` | `--max-shift-tolerance` | number | 否 | 0 | 最小值: 0 | 切点偏移容忍度，单位为秒；默认值为 0，最小值为 0。当该值大于 0 时，会在切点前后该范围内寻找更贴近语义的位置，如句末、停顿。该值越大，切点越贴合语义，但切片实际时长相对 min_duration 或 max_duration 的抖动也越大；必须小于或等于 min_duration。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的对象存储（TOS）桶，可设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要授权 AI MediaKit 将文件写入您的 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `min_duration` | `--min-duration` | number | 否 | 3 | 最小值: 1 | 单个切片的目标最小时长，单位为秒；默认值为 3，最小值为 1。小于该时长的片段会与相邻切片合并，前提是合并后不超过 max_duration，以避免产生过短碎片；必须小于或等于 max_duration。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 是 | - | 格式: "^(http\|https\|mediakit\|vod\|tos)://" | 待处理的视频 URL；支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 (vod://) 和火山引擎对象存储 (tos://) 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；单个视频时长不得超过 3 小时。 |

### 调用示例

```bash
mediakit-cli video semantic-segment \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 输入视频的总时长，单位为秒。 |
| `result.result_url` | string | 否 | Cloud 终态 | 语义切片结果文件地址；未设置 media_output_destination 时，返回有效期为 24 小时的 HTTPS 临时下载链接；设置 media_output_destination 后，返回 tos://<桶名>/<对象Key> 格式的存储地址。文件为 gzip 压缩后的 JSON，包含 source、duration_ms、duration、has_audio、segment_count、segments 等字段。 |
| `result.segment_count` | integer | 否 | Cloud 终态 | 最终切分出的语义片段数量。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video semantic-segment --help
mediakit-cli video semantic-segment --schema
```
