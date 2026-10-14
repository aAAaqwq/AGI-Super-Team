# 视频转封装

## 能力用途

视频转封装用于调整视频容器格式，仅修改容器格式，不会重新编解码音视频码流，适用于点播分发适配、流媒体切片打包与多端兼容等场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video remux-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 数组参数（`--metadata-keep-tags`）传多个值时用逗号分隔并整体加引号，例如 `--metadata-keep-tags "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--metadata-add-tags`）需传合法 JSON 字符串并整体加单引号，例如 `--metadata-add-tags '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video remux-video \
  --video-url <video_url> \
  --container-format <container_format>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `container_format` | `--container-format` | string | 是 | "MP4" | 枚举: ["MP4","FLV","MPEGTS"] | 目标封装格式，支持 MP4、FLV、MPEGTS，默认值为 MP4。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `metadata_add_tags` | `--metadata-add-tags` | array<object> | 否 | - | - | 可选填写需要为输出视频新增的元信息标签列表，每个标签由 key 和 value 组成；对 MPEGTS 封装格式无效；新增标签与被保留标签同名时，会覆盖源文件的值。 |
| `metadata_add_tags[].key` | - | string | 否 | - | - | 标签键。 |
| `metadata_add_tags[].value` | - | string | 否 | - | - | 标签值。 |
| `metadata_keep_tags` | `--metadata-keep-tags` | array<string> | 否 | - | - | 可选填写需要从源视频保留的元信息标签列表，用于指定需要保留的标签键（Key）；默认情况下转码过程会丢弃大部分元信息（如标题、艺术家等）；对 MPEGTS 封装格式无效。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待处理视频的 URL，支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 视频时长，单位为秒。 |
| `result.video_url` | string | 否 | Cloud 终态 | 输出视频地址。未设置 media_output_destination 时，返回 HTTPS 临时下载链接，有效期为 24 小时；设置 media_output_destination 后，返回存储地址，格式为 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key>。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video remux-video --help
mediakit-cli video remux-video --schema
```
