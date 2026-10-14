# 高光智剪-影视拆条

## 能力用途

支持面向电影、电视剧等长视频内容，按剧情故事线识别高光并拆分成多段指定时长的高光片段，用于影视合集分发的短视频素材；算法会识别并去除景色铺垫、缓慢运镜、片头片尾曲等低密度信息；每段拆条带有高光前置开场与结尾钩子设计。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video generate-highlights-movie`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-generate-video`）只能写成 `--enable-generate-video=true` 或 `--enable-generate-video=false`，也可用裸 `--enable-generate-video`（等价 true）；禁止空格传值 `--enable-generate-video true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 对象或对象数组参数（`--highlight-cuts-param`、`--opening-hook-param`）需传合法 JSON 字符串并整体加单引号，例如 `--highlight-cuts-param '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video generate-highlights-movie \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `enable_generate_video` | `--enable-generate-video` | boolean | 否 | true | - | enable_generate_video 默认值为 true；为 true 时生成拆条视频文件，并在结果中返回 video_urls；为 false 时仅输出时间戳、评分、标题等片段元信息，不生成视频文件，可用于自定义二次剪辑。 |
| `highlight_cuts_param` | `--highlight-cuts-param` | object | 否 | - | - | highlight_cuts_param 控制每段拆条的目标时长范围以及是否返回详细片段时间线信息；留空时默认生成 90\-180 秒的拆条片段。 |
| `highlight_cuts_param.enable_detailed_info` | - | boolean | 否 | false | - | enable_detailed_info 默认值为 false；控制是否在 clips 中输出每段拆条的片段类型、评分及原始视频和拆条视频中的起止时间等详细信息。 |
| `highlight_cuts_param.max_duration` | - | number | 否 | 180 | 最小值: 1；最大值: 600 | max_duration 表示单个拆条片段的最大时长，单位为秒；默认值为 180 秒；范围为 1 到 600；建议不超过 180 秒（3 分钟）以贴合短视频平台分发节奏。 |
| `highlight_cuts_param.min_duration` | - | number | 否 | 90 | 最小值: 1；最大值: 600 | min_duration 表示单个拆条片段的最短时长，单位为秒；默认值为 90 秒；范围为 1 到 600。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `opening_hook_param` | `--opening-hook-param` | object | 否 | - | - | opening_hook_param 控制是否在每个拆条片段开头拼接最精彩的钩子片段；留空时默认添加 5\-15 秒的高光前置。 |
| `opening_hook_param.is_enabled` | - | boolean | 否 | true | - | is_enabled 默认值为 true；为 true 时系统自动提取最精彩片段置于拆条视频开头；为 false 时按原始剧情顺序输出拆条视频。 |
| `opening_hook_param.max_duration` | - | number | 否 | 15 | 最小值: 0；最大值: 60 | opening_hook_param.max_duration 默认值为 15 秒，范围为 0 到 60。 |
| `opening_hook_param.min_clip_duration` | - | number | 否 | 5 | 最小值: 0；最大值: 60 | min_clip_duration 是构成高光前置的单个片段最短时长，用于避免碎片过多造成频闪；默认值为 5；范围为 0 到 60。 |
| `opening_hook_param.min_duration` | - | number | 否 | 5 | 最小值: 0；最大值: 60 | opening_hook_param.min_duration 默认值为 5 秒，范围为 0 到 60。 |
| `opening_hook_param.min_score` | - | number | 否 | 4 | 最小值: 0；最大值: 5 | min_score 是筛选高光前置片段的最低评分，数值越高表示筛选标准越严格；默认值为 4；范围为 0 到 5。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待处理的影视视频源 URL；支持公网 HTTP/HTTPS URL、本地文件路径、vod:// 和 tos:// 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；单次任务仅支持单个视频文件；输入视频最高支持 1080p 分辨率，时长不得超过 180 分钟，必须同时包含视频流和音频流；输入更适合电影，也适用于电视剧等长视频内容，不建议用于纯综艺、纪录片、广告或纯 BGM 视频；建议音频轨道包含清晰可识别的中文对话文本，以帮助算法准确理解剧情逻辑。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.input_duration` | number | 否 | Cloud 终态 | input_duration 是输入视频总时长，单位为秒。 |
| `result.result_cuts_info` | array<object> | 否 | Cloud 终态 | result_cuts_info 的条目顺序与 video_urls 一致。 |
| `result.result_cuts_info[].clips` | array<object> | 否 | Cloud 终态 | clips 仅在 highlight_cuts_param.enable_detailed_info 为 true 时返回。 |
| `result.result_cuts_info[].clips[].cut_end_time` | number / null | 否 | Cloud 终态 | cut_end_time 是片段在最终拆条视频中的结束时间点，单位为秒。 |
| `result.result_cuts_info[].clips[].cut_start_time` | number / null | 否 | Cloud 终态 | cut_start_time 是片段在最终拆条视频中的起始时间点，单位为秒。 |
| `result.result_cuts_info[].clips[].score` | number / null | 否 | Cloud 终态 | score 是片段高光评分，范围为 [1, 5]。 |
| `result.result_cuts_info[].clips[].source_end_time` | number / null | 否 | Cloud 终态 | source_end_time 是片段在原始视频中的结束时间点，单位为秒。 |
| `result.result_cuts_info[].clips[].source_start_time` | number / null | 否 | Cloud 终态 | source_start_time 是片段在原始视频中的起始时间点，单位为秒。 |
| `result.result_cuts_info[].clips[].type` | string | 否 | Cloud 终态 | type 表示片段类型：OpeningHook（高光前置）或 HighlightClip（高光主体）。 |
| `result.result_cuts_info[].duration` | number / null | 否 | Cloud 终态 | duration 是拆条视频实际时长，单位为秒。 |
| `result.result_cuts_info[].size` | integer / string / null | 否 | Cloud 终态 | size 是拆条视频文件大小，单位为字节。 |
| `result.result_cuts_info[].title` | string | 否 | Cloud 终态 | title 是算法基于剧情自动生成的片段标题或内容简述。 |
| `result.result_cuts_info[].video_url` | string | 否 | Cloud 终态 | video_url 是该拆条片段对应的视频地址；未生成视频时 video_url 为空字符串；video_url 的有效期为 24 小时，需及时保存。 |
| `result.video_urls` | array<string> | 否 | Cloud 终态 | enable_generate_video 为 false 或算法未成功生成视频时，video_urls 为空。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video generate-highlights-movie --help
mediakit-cli video generate-highlights-movie --schema
```
