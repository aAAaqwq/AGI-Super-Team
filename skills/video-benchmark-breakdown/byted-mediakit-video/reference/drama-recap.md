# 解说视频生成

## 能力用途

基于已完成的剧本还原任务，可使用自定义解说词或由 AI 自动生成解说词，生成带 AI 配音与解说字幕的营销或解说视频；可配置音色、字幕样式与原文字幕擦除。


## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video drama-recap`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- `--drama-script-task-id` 必须来自已完成的剧本还原终态结果。若用户未提供：先调用 [drama-script.md](drama-script.md)，轮询至终态后读取 `result.drama_script_task_id`，再调用本工具；禁止猜测或伪造。
- 布尔参数（`--erase-subtitle`）只能写成 `--erase-subtitle=true` 或 `--erase-subtitle=false`，也可用裸 `--erase-subtitle`（等价 true）；禁止空格传值 `--erase-subtitle true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 对象或对象数组参数（`--drama-recap-config`、`--miniseries-edit`、`--speaker-config`、`--subtitle-config`）需传合法 JSON 字符串并整体加单引号，例如 `--drama-recap-config '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video drama-recap \
 --drama-script-task-id <drama_script_task_id>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `batch_count` | `--batch-count` | integer | 否 | 1 | 最小值: 1；最大值: 100 | 批量生成解说视频数量。 |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `drama_recap_config` | `--drama-recap-config` | object | 否 | - | - | 解说文案与生成策略配置对象。 |
| `drama_recap_config.auto_generate_recap` | - | boolean | 否 | false | - | 是否由 AI 自动生成解说词。true 时不能设置 recap_text。 |
| `drama_recap_config.enable_repeat_match` | - | boolean | 否 | false | - | 是否允许解说词匹配重复的视频画面。 |
| `drama_recap_config.pause_time` | - | integer | 否 | 120 | 最小值: 1；最大值: 1000 | AI 配音句间停顿时长（毫秒），取值范围 [1, 1000]。 |
| `drama_recap_config.prefer_speed` | - | boolean | 否 | false | - | 是否优先生成速度。 |
| `drama_recap_config.style` | - | string | 否 | - | 最长长度: 500 | AI 生成解说词的风格指令，如悬疑、搞笑、轻松等。仅 auto_generate_recap=true 时有效。 |
| `drama_recap_config.text_length` | - | integer | 否 | - | 最小值: 1；最大值: 5000 | AI 生成解说词的期望长度（UTF-8 字符数），仅 auto_generate_recap=true 时有效。 |
| `drama_recap_config.text_speed` | - | number | 否 | 1 | 最小值: 0.5；最大值: 2 | 解说词语速，取值范围 [0.5, 2.0]。 |
| `drama_script_task_id` | `--drama-script-task-id` | string | 是 | - | 最短长度: 1 | 已成功完成的剧本还原任务的 task_id（对应剧本还原终态结果 `result.drama_script_task_id`）。用户未提供时：先按 [drama-script.md](drama-script.md) 提交并完成剧本还原，再取终态 `result.drama_script_task_id` 填入本参数；不得编造、猜测或使用未完成任务的 ID。 |
| `erase_mode` | `--erase-mode` | string | 否 | "standard" | 枚举: ["standard"] | 字幕擦除模式。仅 erase_subtitle=true 时生效；当前仅支持 standard。 |
| `erase_subtitle` | `--erase-subtitle` | boolean | 否 | false | - | 是否擦除原视频中的字幕。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `miniseries_edit` | `--miniseries-edit` | object | 否 | - | - | 短剧三要素视觉模板配置对象。仅适用于竖屏短剧。 |
| `miniseries_edit.hint` | - | string | 否 | - | 最长长度: 20 | 短剧提示语，不超过 20 个字。 |
| `miniseries_edit.template` | - | string | 否 | - | 枚举: ["热门短剧1","热门短剧2","热门短剧3","热门短剧4","热门短剧5"] | 短剧三要素视觉模板名称。 |
| `miniseries_edit.title` | - | string | 否 | - | 最长长度: 15 | 短剧名称，不超过 15 个字。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `recap_text` | `--recap-text` | string | 否 | - | 最长长度: 5000 | 自定义解说词文本。当 drama_recap_config.auto_generate_recap=false（默认）时必填；为 true 时不可设置。 |
| `speaker_config` | `--speaker-config` | object | 否 | - | - | 配音配置对象。推荐使用该对象组织音色相关参数；未传时按默认音色处理。 |
| `speaker_config.voice_type` | - | string | 否 | "Yunxi" | 枚举: ["Yunxi","Yunjian","Yunfeng","Yunyi","Yunjie","Yunze","Yunye","Xiaoxiao","Xiaochen","Xiaohan","Xiaomo"] | 音色名称。预置音色：Yunxi / Yunjian / Yunfeng / Yunyi / Yunjie / Yunze / Yunye / Xiaoxiao / Xiaochen / Xiaohan / Xiaomo。 |
| `subtitle_config` | `--subtitle-config` | object | 否 | - | - | 字幕样式配置对象。可按需只传部分字段，未传字段按默认行为处理。 |
| `subtitle_config.align_type` | - | integer | 否 | 1 | - | 文本对齐方式。横排：0=左对齐，1=居中，2=右对齐；竖排：1=居中，3=上对齐，4=下对齐。 |
| `subtitle_config.alpha` | - | number | 否 | 1 | 最小值: 0；最大值: 1 | 字体透明度，取值范围 [0,1]。0 为透明。默认为 1。 |
| `subtitle_config.background_border_size` | - | number | 否 | 0 | 最小值: 0 | 字幕背景边框大小。 |
| `subtitle_config.background_color` | - | string | 否 | "#00000000" | - | 字幕背景颜色，RGBA 格式。 |
| `subtitle_config.border_color` | - | string | 否 | "#00000000" | - | 字幕描边颜色，RGBA 格式。 |
| `subtitle_config.border_width` | - | integer | 否 | - | 最小值: 1 | 字幕描边宽度（pixel）。 |
| `subtitle_config.bottom_right_x` | - | integer | 否 | - | 最小值: 1 | 字幕矩形区域右下角 X 坐标（pixel）。需大于 top_left_x。 |
| `subtitle_config.bottom_right_y` | - | integer | 否 | - | 最小值: 1 | 字幕矩形区域右下角 Y 坐标（pixel）。需大于 top_left_y。 |
| `subtitle_config.disable_subtitle` | - | boolean | 否 | false | - | 是否不在生成的解说视频中添加新字幕。 |
| `subtitle_config.font_color` | - | string | 否 | "#FFFFFFFF" | - | 字幕字体颜色，RGBA 格式（如 "#FFCC66FF"）。 |
| `subtitle_config.font_size` | - | integer | 否 | - | 最小值: 1 | 字幕字体大小（pixel）。 |
| `subtitle_config.font_type` | - | string | 否 | "sy_black" | 枚举: ["sy_black","pm_zhengdao"] | 字幕字体类型。仅支持 sy_black(思源黑体)、pm_zhengdao(庞门正道标题体)。 |
| `subtitle_config.line_max_width` | - | number | 否 | 1 | 最小值: 0；最大值: 1 | 自动换行宽度占比，取值 [0,1]。 |
| `subtitle_config.top_left_x` | - | integer | 否 | - | 最小值: 0 | 字幕矩形区域左上角 X 坐标（pixel）。 |
| `subtitle_config.top_left_y` | - | integer | 否 | - | 最小值: 0 | 字幕矩形区域左上角 Y 坐标（pixel）。 |
| `subtitle_config.typesetting` | - | integer | 否 | 0 | 枚举: [0,1] | 文字排列方向：0=横排，1=竖排。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number / null | 否 | Cloud 终态 | 输出视频时长（秒）。 |
| `result.error` | object / null | 否 | Cloud 终态 | 错误信息（失败时返回）。 |
| `result.error.code` | string / null | 否 | Cloud 终态 | 失败时返回的错误码。 |
| `result.error.message` | string / null | 否 | Cloud 终态 | 失败时返回的错误信息。 |
| `result.failed_count` | integer / null | 否 | Cloud 终态 | 失败数量。 |
| `result.success_count` | integer / null | 否 | Cloud 终态 | 成功生成数量。 |
| `result.total_count` | integer / null | 否 | Cloud 终态 | 批量生成总数（batch_count>1 时返回）。 |
| `result.video_url` | string / null | 否 | Cloud 终态 | 生成的解说视频 URL（batch_count=1 时返回）。 |
| `result.video_urls` | array<string> | 否 | Cloud 终态 | 生成的解说视频 URL 列表（batch_count>1 时返回）。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video drama-recap --help
mediakit-cli video drama-recap --schema
```
