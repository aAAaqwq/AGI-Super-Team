# 场景切分

## 能力用途

依据视频的转场和画面内容变化自动切分多个场景片段，输出每个场景片段的时间轴信息与对应的独立视频文件。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video segment-scenes`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-clip-fade`、`--return-segment-videos`）只能写成 `--enable-clip-fade=true` 或 `--enable-clip-fade=false`，也可用裸 `--enable-clip-fade`（等价 true）；禁止空格传值 `--enable-clip-fade true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli video segment-scenes \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `enable_clip_fade` | `--enable-clip-fade` | boolean | 否 | false | - | enable_clip_fade 控制是否将检测到的淡入或淡出片段作为独立切片输出。enable_clip_fade 的默认值为 false。enable_clip_fade 为 true 且视频存在明显淡入或淡出过渡时，会将其分割为独立切片。enable_clip_fade 为 false 时不独立输出淡入或淡出片段，而将其视为前后场景的一部分并合并到相邻切片。 |
| `max_duration` | `--max-duration` | number | 否 | - | 最小值: 0 | max_duration 表示单个切片的最大时长，单位为秒。max_duration 的默认值为 30 秒。max_duration 必须大于或等于 min_duration。大于 max_duration 的片段将被强制切分。 |
| `min_duration` | `--min-duration` | number | 否 | - | 最小值: 0 | min_duration 表示单个切片的最小时长，单位为秒。min_duration 的默认值为 3 秒。小于 min_duration 的片段将被合并。min_duration 必须小于或等于 max_duration。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `return_segment_videos` | `--return-segment-videos` | boolean | 否 | true | - | return_segment_videos 的默认值为 true。return_segment_videos 为 true 时生成切片文件，并在 result.segments[].segment_video_url 返回各切片下载链接。return_segment_videos 为 false 时不生成切片文件，仅返回 start_time 和 end_time 切片时间轴，不返回 segment_video_url。false 可用于只需获取场景时间码并由业务侧自行处理切片的场景，可降低任务耗时。 |
| `segment_threshold` | `--segment-threshold` | number | 否 | - | 最小值: 0；最大值: 100 | segment_threshold 是场景切分的敏感度阈值，最小值为 0，必须小于 100。取值越低，算法对场景变化越敏感，切分出的片段越多；取值越高，算法越倾向将微小变化视为同一场景，切分出的片段越少。同时设置 min_duration、max_duration 和 segment_threshold 时，系统采用两阶段逻辑以满足全部约束：第一阶段根据 segment_threshold 和 min_duration 进行切分；第一阶段后如有切片时长超过 max_duration，系统忽略 segment_threshold 再次切分，确保最终时长不超过 max_duration。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待处理的视频 URL。视频来源支持公网 HTTP/HTTPS URL、本地文件路径、火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议。支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。单个视频时长必须不超过 2 小时。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | result.duration 是输入视频的总时长，单位为秒。 |
| `result.segments` | array<object> | 否 | Cloud 终态 | result.segments 是切片信息列表，每个元素包含切片起止时间等信息。 |
| `result.segments[].end_time` | number | 否 | Cloud 终态 | result.segments[].end_time 是切片的结束时间，单位为秒。 |
| `result.segments[].segment_video_url` | string | 否 | Cloud 终态 | result.segments[].segment_video_url 是切片视频文件的下载地址。切片输出视频为 MP4 格式。仅当 return_segment_videos 为 true（默认）时返回 segment_video_url；return_segment_videos 为 false 时不生成切片文件且不返回 segment_video_url。切片视频文件下载地址的有效期为 24 小时。 |
| `result.segments[].start_time` | number | 否 | Cloud 终态 | result.segments[].start_time 是切片的起始时间，单位为秒。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video segment-scenes --help
mediakit-cli video segment-scenes --schema
```
