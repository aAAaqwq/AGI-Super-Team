# 视频抽帧

## 能力用途

从视频中抽取截图，截图结果支持用于视频封面、预览图、雪碧图或其他视频理解任务的输入。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video extract-frames`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-sprite`）只能写成 `--enable-sprite=true` 或 `--enable-sprite=false`，也可用裸 `--enable-sprite`（等价 true）；禁止空格传值 `--enable-sprite true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli video extract-frames \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `enable_sprite` | `--enable-sprite` | boolean | 否 | false | - | 默认 false。设为 true 时输出包含所有截图的雪碧图；设为 false 时输出多张独立截图。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `scale_long` | `--scale-long` | integer | 否 | - | 最小值: 0；最大值: 4096 | scale_long 最小值为 0，最大值为 4096。输出图片长边不得超过原始视频长边。按长边缩放时，输出图片短边按原始比例自适应。enable_sprite 为 true 时，scale_long 定义单张小图的长边。同时设置 scale_long 和 scale_short 时保持原始宽高比，并分别约束长边和短边。 |
| `scale_short` | `--scale-short` | integer | 否 | - | 最小值: 0；最大值: 4096 | scale_short 最小值为 0，最大值为 4096。输出图片短边不得超过原始视频短边。按短边缩放时，输出图片长边按原始比例自适应。enable_sprite 为 true 时，scale_short 定义单张小图的短边。同时设置 scale_long 和 scale_short 时保持原始宽高比，并分别约束长边和短边。 |
| `scene_change_threshold` | `--scene-change-threshold` | number | 否 | 0.1 | 最小值: 0；最大值: 1 | scene_change_threshold 默认值为 0.1。scene_change_threshold 必须大于 0 且必须小于 1。scene_change_threshold 仅在 snapshot_type 为 SceneChange 时生效。scene_change_threshold 越小，场景变化检测越敏感，可能产生更多截图。 |
| `snapshot_limit` | `--snapshot-limit` | integer | 否 | - | 最小值: 1；最大值: 1000 | snapshot_limit 最小值为 1，最大值为 1000。实际输出的截图数可能小于 snapshot_limit。snapshot_limit 仅在 snapshot_type 为 TimeInterval 或 SceneChange 时生效。enable_sprite 为 true 时，snapshot_limit 表示雪碧图大图数量上限，小图数量上限为 snapshot_limit*sprite_rows*sprite_cols。 |
| `snapshot_type` | `--snapshot-type` | string | 否 | "TimeInterval" | 枚举: ["TimeInterval","SpecifiedTime","SpecifiedFrames","SceneChange"] | snapshot_type 决定抽帧的具体方式，默认为 TimeInterval，支持 TimeInterval、SpecifiedTime、SpecifiedFrames 和 SceneChange 四个字面值。TimeInterval 表示按时间间隔抽帧，并需配合 time_interval。SpecifiedTime 表示按指定时间点抽帧，并需配合 specified_time。SpecifiedFrames 表示按指定帧号抽帧，并需配合 specified_frames。SceneChange 表示按场景变化抽帧，并需配合 scene_change_threshold。 |
| `specified_frames` | `--specified-frames` | array<integer> | 否 | - | 最少项数: 1；最多项数: 2；元素枚举: [0,-1] | specified_frames 当前仅支持 0 表示视频首帧、-1 表示视频尾帧，最多支持 2 个值。 |
| `specified_time` | `--specified-time` | array<number> | 否 | - | 最少项数: 1；最多项数: 1000 | specified_time 中时间点的单位为秒，支持最多 3 位小数，最多支持 1000 个时间点。 |
| `sprite_cols` | `--sprite-cols` | integer | 否 | 10 | 最小值: 1；最大值: 100 | sprite_cols 表示雪碧图在 X 轴水平方向的小图数量，默认值为 10，最小值为 1，最大值为 100。sprite_cols 仅在 enable_sprite 为 true 时生效。过大的雪碧图行列数可能导致任务失败，雪碧图建议单边不超过 16384 像素。 |
| `sprite_rows` | `--sprite-rows` | integer | 否 | 10 | 最小值: 1；最大值: 100 | sprite_rows 表示雪碧图在 Y 轴垂直方向的小图数量，默认值为 10，最小值为 1，最大值为 100。sprite_rows 仅在 enable_sprite 为 true 时生效。过大的雪碧图行列数可能导致任务失败，雪碧图建议单边不超过 16384 像素。 |
| `time_interval` | `--time-interval` | number | 否 | 1 | 最小值: 0.001 | time_interval 默认值为 1，单位为秒，支持最多 3 位小数，必须大于 0.001。time_interval 仅在 snapshot_type 为 TimeInterval 时生效。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待处理的视频 URL，支持公网 HTTP/HTTPS URL、本地文件路径、vod:// 和 tos:// 四种输入协议。视频输入支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.snapshot_count` | integer | 否 | Cloud 终态 | snapshot_count 是成功生成的截图总数；雪碧图模式下，snapshot_count 表示雪碧图中的小图数量。 |
| `result.snapshots` | array<object> | 否 | Cloud 终态 | snapshots 是截图结果列表，每个对象包含一张截图的信息。 |
| `result.snapshots[].image_url` | string | 否 | Cloud 终态 | image_url 是截图下载地址，有效期为 24 小时，需及时保存产物。enable_sprite 为 true 时，snapshots 数组中的 image_url 指向合成后的雪碧图大图。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video extract-frames --help
mediakit-cli video extract-frames --schema
```
