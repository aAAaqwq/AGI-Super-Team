# 生成式画质增强

## 能力用途

基于 Diffusion 扩散大模型技术提供生成式视频增强与修复，通过深度语义理解，智能补全和生成符合视频内容的真实细节，可修复视频在压缩或老化过程中损失的像素，最终产出自然、高保真的视频画面。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video enhance-video-generative`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `bitrate_level` | `--bitrate-level` | string | 否 | "medium" | 枚举: ["low","medium","high"] | bitrate_level 是控制输出视频平均码率的目标码率档位，会影响视频的视觉质量和最终文件体积；high 表示高码率，medium 表示中码率且为推荐档位，low 表示低码率；默认值为 medium。 |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `fps` | `--fps` | number | 否 | - | 最小值: 15；最大值: 120 | fps 指定目标帧率，单位为 fps；支持范围为 [15, 120]；建议不超过原片帧率的 4 倍；未指定 fps 时，输出视频保持与原始片源一致的帧率。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `resolution` | `--resolution` | string | 否 | "720p" | 枚举: ["720p","1080p","2k"] | resolution 指定目标分辨率；支持 720p、1080p、2k；默认值为 720p。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待增强的视频 URL；支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议；仅支持 SDR 视频；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入视频最高支持 1080p，长边范围为 [360,1920]，短边范围为 [360,1080]。 |

### 调用示例

```bash
mediakit-cli video enhance-video-generative \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | result.duration 是输出视频的总时长，单位为秒。 |
| `result.fps` | number | 否 | Cloud 终态 | result.fps 是输出视频的帧率。 |
| `result.resolution` | string | 否 | Cloud 终态 | result.resolution 是输出视频的分辨率。 |
| `result.video_url` | string | 否 | Cloud 终态 | result.video_url 是增强后的视频文件地址；未设置 media_output_destination 时，result.video_url 返回有效期为 24 小时的 HTTPS 临时下载链接，需要及时下载保存；设置 media_output_destination 后，result.video_url 返回 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key> 的存储地址。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果。生成式增强耗时常超过单次 query-task 的 9 分钟轮询上限；若返回 `status: running` 且命令正常退出，属预期行为，用同一 `task_id` 继续 `--poll-complete`。

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video enhance-video-generative --help
mediakit-cli video enhance-video-generative --schema
```
