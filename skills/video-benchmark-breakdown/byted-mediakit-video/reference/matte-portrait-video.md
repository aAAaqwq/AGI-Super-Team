# 视频人像抠图

## 能力用途

自动识别视频中的人物主体，移除原始背景，并生成背景透明或纯色背景的视频文件，适用于背景替换等后期处理场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video matte-portrait-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `background_color` | `--background-color` | string | 否 | - | 枚举: ["black","white","green"] | 输出视频的背景颜色；black 表示黑色，white 表示白色，green 表示绿色，默认为绿色；仅当 format 为 MP4 时生效。 |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数；任务完成时会通过事件回调原样返回，用于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址；提供后优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 默认不传。用户明确指定时原样使用；用户明确要求重试时，同一逻辑请求的重试链必须复用同一 token。已有 token 时必须复用原值；此前请求未带 token 时，可从本次重试开始创建一次并持续复用，但该 token 不对此前请求提供追溯幂等。业务参数变化视为新请求，不得复用旧 token。不得为每次尝试生成不同值。CLI/MCP runtime 不判断重试意图，也不自动生成 token。 |
| `format` | `--format` | string | 否 | "WEBM" | 枚举: ["MOV","WEBM","MP4"] | 输出视频的格式，默认为 WEBM。MP4 输出 MP4 格式和纯色背景，并可选用 background_color 指定背景颜色。MOV 输出 QuickTime Movie 格式和透明背景，支持 Alpha 透明通道。WEBM 输出 WebM 格式和透明背景，支持 Alpha 透明通道。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置；支持将处理产物存储至火山引擎视频点播（VOD）空间或对象存储（TOS）桶。存储至 VOD 时设为 `vod://<您的空间名>`，存储至 TOS 时设为 `tos://<您的桶名>`。设置后，任务结果中的 `url` 相关字段返回 `vod://` 或 `tos://` 格式的资源地址，不再返回临时下载地址。首次使用前需按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID；不传时默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以按队列对应的项目进行分账。队列可创建和管理，系统会自动分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 是 | - | - | 指定待抠图的视频 URL，支持 mp4、flv、ts、avi、mov、mkv、wmv 等主流视频格式；支持公网 HTTP/HTTPS URL、本地文件路径、视频点播 vod:// 和对象存储 tos:// 四种输入协议。 |

### 调用示例

```bash
mediakit-cli video matte-portrait-video \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 任务结果查询

提交成功后会返回 `task_id`，再执行 `mediakit-cli shared query-task --task-id <task_id>` 查询。

- 当前命令：`mediakit-cli video matte-portrait-video`
- 推荐查询：`mediakit-cli shared query-task --task-id <task_id>`

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video matte-portrait-video --help
mediakit-cli video matte-portrait-video --schema
```
