# 高光智剪-小游戏

## 能力用途

支持识别小游戏录屏视频中的核心玩法与高光事件，例如连击、通关、极限操作，并快速生成用于买量推广的视频素材。可选提供游戏名称、玩法描述和高光定义，辅助更精准地识别精彩内容。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video generate-highlights-minigame`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-generate-video`）只能写成 `--enable-generate-video=true` 或 `--enable-generate-video=false`，也可用裸 `--enable-generate-video`（等价 true）；禁止空格传值 `--enable-generate-video true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--minigame-info`）需传合法 JSON 字符串并整体加单引号，例如 `--minigame-info '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video generate-highlights-minigame \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `enable_generate_video` | `--enable-generate-video` | boolean | 否 | true | - | 控制是否生成高光混剪视频，默认 true。true 时生成并输出高光混剪视频；false 时不生成高光混剪视频。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `minigame_info` | `--minigame-info` | object | 否 | - | - | 可选的小游戏描述信息，建议填写以辅助模型更精准地识别高光内容。 |
| `minigame_info.highlight_definition` | - | string | 否 | - | 最长长度: 5000 | 游戏高光时刻或精彩瞬间定义，例如一次消除多个方块或躲避所有障碍物通关。 |
| `minigame_info.name` | - | string | 否 | - | 最长长度: 5000 | 游戏名称，用于标识游戏内容。 |
| `minigame_info.play_definition` | - | string | 否 | - | 最长长度: 5000 | 游戏玩法规则或核心特点描述。 |
| `mode` | `--mode` | string | 否 | "HighlightExtract" | 枚举: ["HighlightExtract"] | 高光提取模式，当前版本固定为 HighlightExtract。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 1 | 待处理小游戏视频 URL 列表。单次任务仅支持输入 1 个视频文件；支持公网 HTTP/HTTPS、本地文件路径、视频点播 vod:// 和对象存储 tos:// 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入文件时长不得超过 10 分钟；输入分辨率最高支持 1080p。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 输入视频总时长，单位为秒。 |
| `result.mixvideo_info` | array<object> | 否 | Cloud 终态 | 高光混剪视频信息列表，每项包含构成该混剪的高光片段。 |
| `result.mixvideo_info[].clips` | array<object> | 否 | Cloud 终态 | 构成当前混剪视频的高光片段对象列表。 |
| `result.mixvideo_info[].clips[].clip_type` | string | 否 | Cloud 终态 | 片段类型，HighlightClip 代表普通高光片段。 |
| `result.mixvideo_info[].clips[].cut_end_time` | number | 否 | Cloud 终态 | 片段在最终混剪视频中的结束时间，单位为秒。 |
| `result.mixvideo_info[].clips[].cut_start_time` | number | 否 | Cloud 终态 | 片段在最终混剪视频中的起始时间，单位为秒。 |
| `result.mixvideo_info[].clips[].score` | number | 否 | Cloud 终态 | 分数越高表示片段越精彩。 |
| `result.mixvideo_info[].clips[].source_end_time` | number | 否 | Cloud 终态 | 片段在原始视频中的结束时间，单位为秒。 |
| `result.mixvideo_info[].clips[].source_start_time` | number | 否 | Cloud 终态 | 片段在原始视频中的起始时间，单位为秒。 |
| `result.mixvideo_info[].clips[].source_video_index` | integer | 否 | Cloud 终态 | 该片段在输入视频列表中的来源索引位置；小游戏高光智剪仅支持输入单个视频，来源索引固定为 0。 |
| `result.mixvideo_info[].mixvideo_index` | integer | 否 | Cloud 终态 | 混剪视频索引，与 video_urls 的位置一一对应，并从 0 开始。 |
| `result.mixvideo_info[].video_url` | string | 否 | Cloud 终态 | 当前混剪信息项对应的混剪视频地址。enable_generate_video 为 false 时不返回；未设置 media_output_destination 时，返回有效期为 24 小时的 HTTPS 临时下载链接；设置 media_output_destination 后，返回 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key> 格式的存储地址。 |
| `result.video_urls` | array<string> | 否 | Cloud 终态 | 最终生成的高光混剪视频地址列表。enable_generate_video 为 false 时不返回；未设置 media_output_destination 时，返回有效期为 24 小时的 HTTPS 临时下载链接；设置 media_output_destination 后，返回 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key> 格式的存储地址。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video generate-highlights-minigame --help
mediakit-cli video generate-highlights-minigame --schema
```
