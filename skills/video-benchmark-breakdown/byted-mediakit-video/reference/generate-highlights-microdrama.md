# 高光智剪-短剧

## 能力用途

可用于短剧高光智剪，基于输入剧集的角色和剧情故事线理解提取高光片段，并按时长、产出个数、顺剪或跳剪等要求生成高光混剪、单集预告等视频。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video generate-highlights-microdrama`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-generate-video`、`--enable-return-poster`、`--enable-segment-tag`）只能写成 `--enable-generate-video=true` 或 `--enable-generate-video=false`，也可用裸 `--enable-generate-video`（等价 true）；禁止空格传值 `--enable-generate-video true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--edit-param`、`--highlight-cuts-param`、`--opening-hook-param`）需传合法 JSON 字符串并整体加单引号，例如 `--edit-param '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video generate-highlights-microdrama \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数；任务完成时会通过事件回调原样返回，用于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址；提供后优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 默认不传。用户明确指定时原样使用；用户明确要求重试时，同一逻辑请求的重试链必须复用同一 token。已有 token 时必须复用原值；此前请求未带 token 时，可从本次重试开始创建一次并持续复用，但该 token 不对此前请求提供追溯幂等。业务参数变化视为新请求，不得复用旧 token。不得为每次尝试生成不同值。CLI/MCP runtime 不判断重试意图，也不自动生成 token。 |
| `edit_param` | `--edit-param` | object | 否 | - | - | 高光视频剪辑配置用于控制最终输出视频的视觉风格；留空时默认使用基础剪辑模式。enable_generate_video 为 false 时，该配置将被忽略。 |
| `edit_param.mode` | - | string | 是 | "BasicEdit" | 枚举: ["BasicEdit","TemplateEdit"] | 成片剪辑模式决定是否使用视觉模板，默认为 BasicEdit；支持 BasicEdit 和 TemplateEdit。BasicEdit 表示基础剪辑，不添加额外视觉元素；TemplateEdit 表示模板剪辑，使用指定的短剧三要素视觉模板。 |
| `edit_param.template_edit` | - | object | 否 | - | - | 短剧模板剪辑参数不是无条件必选；当 mode 为 TemplateEdit 时必须填写。 |
| `edit_param.template_edit.hint` | - | string | 否 | - | 最长长度: 20 | 短剧提示语将显示在画面左侧或右侧，长度不得超过 20 个字符。 |
| `edit_param.template_edit.template` | - | string | 否 | "热门短剧1" | 枚举: ["热门短剧1","热门短剧2","热门短剧3","热门短剧4","热门短剧5"] | 短剧三要素视觉模板名称决定剧名、角标、提示语的样式和位置，默认为热门短剧1；支持 热门短剧1、热门短剧2、热门短剧3、热门短剧4、热门短剧5。 |
| `edit_param.template_edit.title` | - | string | 否 | - | 最长长度: 22 | 短剧名称将显示在视频画面中，长度不得超过 22 个字符。 |
| `enable_generate_video` | `--enable-generate-video` | boolean | 否 | true | - | 是否生成高光混剪视频，默认为 true。true 时生成并输出高光混剪视频；false 时不生成高光混剪视频，传入的 edit_param 将被忽略。 |
| `enable_return_poster` | `--enable-return-poster` | boolean | 否 | false | - | 是否在任务结果中返回混剪视频的封面图 URL，默认为 false。true 时返回混剪视频的封面图 URL；false 时不返回封面图。 |
| `enable_segment_tag` | `--enable-segment-tag` | boolean | 否 | - | - | 是否返回高光片段和分镜标签，默认为 false。true 时在 result.mixvideo_info.clips 与 result.storyboard_info 中额外返回 tags 字段；false 时不返回 tags 字段。 |
| `highlight_cuts_param` | `--highlight-cuts-param` | object | 否 | - | - | 高光智剪参数配置用于控制最终输出视频的时长与个数；留空时默认使用热门短剧1模板。 |
| `highlight_cuts_param.cut_mode` | - | string | 否 | "Mixed" | 枚举: ["Mixed","Sequential"] | 剪辑模式默认为 Mixed；支持 Mixed 和 Sequential。Mixed 表示混剪，打乱高光片段的原始顺序；Sequential 表示顺剪，保持高光片段的原始时间顺序。 |
| `highlight_cuts_param.enable_storyboard` | - | boolean | 否 | false | - | 控制是否在任务结果中输出详细的分镜信息 storyboard_info，默认为 false。 |
| `highlight_cuts_param.highlight_ending_prompt` | - | string | 否 | - | - | 高光混剪结尾钩子选取偏好，仅在 cut_mode 为 Mixed 的混剪模式下生效。 |
| `highlight_cuts_param.highlight_segment_prompt` | - | string | 否 | - | - | 高光片段选取偏好，仅在 cut_mode 为 Mixed 的混剪模式下生效。 |
| `highlight_cuts_param.highlight_start_prompt` | - | string | 否 | - | - | 高光混剪开头起播点选取偏好，仅在 cut_mode 为 Mixed 的混剪模式下生效。 |
| `highlight_cuts_param.max_duration` | - | number | 否 | 180 | - | 期望输出高光视频的最大时长，默认为 180。 |
| `highlight_cuts_param.max_number` | - | integer | 否 | 6 | - | 最多输出的高光视频数量，默认为 6。 |
| `highlight_cuts_param.min_duration` | - | number | 否 | 30 | - | 期望输出高光视频的最小时长，默认为 30。 |
| `highlight_cuts_param.user_preferred_segments` | - | array<object> | 否 | - | - | 用户期望优先选用的原片内容或片段，支持填写多个，仅在 cut_mode 为 Mixed 的混剪模式下生效。 |
| `highlight_cuts_param.user_preferred_segments[].end_time` | - | number | 否 | - | - | 优先片段在该输入视频中的结束时间，单位为秒。 |
| `highlight_cuts_param.user_preferred_segments[].episode` | - | integer | 是 | - | 最小值: 0 | 优先选用的输入视频序号，从 0 开始计数；仅含该序号表示整集优先。 |
| `highlight_cuts_param.user_preferred_segments[].start_time` | - | number | 否 | - | - | 优先片段在该输入视频中的起始时间，单位为秒；与 end_time 一并提供时，表示该集指定时间区间优先。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置；支持将处理产物存储至火山引擎视频点播（VOD）空间或对象存储（TOS）桶。存储至 VOD 时设为 `vod://<您的空间名>`，存储至 TOS 时设为 `tos://<您的桶名>`。设置后，任务结果中的 `url` 相关字段返回 `vod://` 或 `tos://` 格式的资源地址，不再返回临时下载地址。首次使用前需按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `mode` | `--mode` | string | 否 | "StorylineCuts" | 枚举: ["StorylineCuts"] | 当前版本固定为 StorylineCuts。 |
| `opening_hook_param` | `--opening-hook-param` | object | 否 | - | - | 精彩前置参数用于控制是否在视频开头添加一个极具吸引力的钩子片段来留住观众；留空时默认在视频开头添加精彩前置片段。 |
| `opening_hook_param.enable_opening_hook` | - | boolean | 否 | true | - | 是否启用精彩前置开场钩子，默认为 true。 |
| `opening_hook_param.max_duration` | - | number | 否 | 15 | - | 开场钩子片段的最大时长，默认为 15。 |
| `opening_hook_param.min_clip_duration` | - | number | 否 | 5 | - | 构成开场钩子的单个高光片段的最小持续时长，默认为 5。 |
| `opening_hook_param.min_duration` | - | number | 否 | 5 | - | 开场钩子片段的最小时长，默认为 5。 |
| `opening_hook_param.min_score` | - | number | 否 | 3 | - | 构成开场钩子的单个高光片段所需达到的最低高光分，范围为 [1, 5]，默认为 3。 |
| `opening_hook_param.opening_hook_prompt` | - | string | 否 | - | - | 精彩前置片段选取标准，用自然语言描述开头钩子的筛选偏好。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID；不传时默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以按队列对应的项目进行分账。队列可创建和管理，系统会自动分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video_ending_mode` | `--video-ending-mode` | string | 否 | - | 枚举: ["ReuseMainEnding","SmartSelect"] | 视频结尾选取模式默认为 ReuseMainEnding；支持 ReuseMainEnding 和 SmartSelect。ReuseMainEnding 时优先复用正片剧集结尾；SmartSelect 时使用智能选取模式。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 100 | 待处理的短剧原片视频 URL 列表。支持公网 HTTP/HTTPS URL、本地文件路径、来源于火山引擎视频点播 vod:// 和火山引擎对象存储 tos:// 四种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入分辨率最高支持 1080p。所有输入文件的累计总时长不得超过 45 分钟。输入素材必须同时包含视频流和音频流，视频画面下半部分必须包含清晰居中的中文字幕，音频轨道中必须包含清晰可识别的中文对话文本。 CLI 传参时可使用逗号分隔多个值，或重复传递该 flag；不要传 JSON 数组字符串。 |

### 任务结果查询

提交成功后会返回 `task_id`，再执行 `mediakit-cli shared query-task --task-id <task_id>` 查询。

- 当前命令：`mediakit-cli video generate-highlights-microdrama`
- 推荐查询：`mediakit-cli shared query-task --task-id <task_id>`

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video generate-highlights-microdrama --help
mediakit-cli video generate-highlights-microdrama --schema
```
