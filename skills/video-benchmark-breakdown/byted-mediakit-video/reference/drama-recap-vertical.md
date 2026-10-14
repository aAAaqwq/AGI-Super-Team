# 解说视频生成（短剧行业模型）

## 能力用途

基于输入短剧剧集的角色与剧情故事线理解，自动提取高光片段并生成全新解说视频；支持文字解说（原片高光混剪 + 屏幕文字）与旁白解说（原片高光混剪 + AI 语音 + BGM），并可套用短剧三要素视觉模板。


## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video drama-recap-vertical`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-return-poster`）只能写成 `--enable-return-poster=true` 或 `--enable-return-poster=false`，也可用裸 `--enable-return-poster`（等价 true）；禁止空格传值 `--enable-return-poster true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--edit-param`、`--narrate-options`、`--text-options`）需传合法 JSON 字符串并整体加单引号，例如 `--edit-param '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video drama-recap-vertical \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `edit_param` | `--edit-param` | object | 否 | - | - | 支持在 narrate 和 text 两种模式中使用；可选配置成片剪辑效果，包括套用包含剧名、角标和提示语的短剧三要素视觉模板。 |
| `edit_param.mode` | - | string | 是 | "BasicEdit" | 枚举: ["BasicEdit","TemplateEdit"] | 默认为 BasicEdit；支持 BasicEdit 和 TemplateEdit，BasicEdit 仅拼接高光片段，TemplateEdit 在基础剪辑上套用短剧三要素视觉模板。 |
| `edit_param.template_edit` | - | object | 否 | - | - | 仅当 edit_param.mode 为 TemplateEdit 时生效。 |
| `edit_param.template_edit.hint` | - | string | 否 | - | 最长长度: 20 | 画面左右两侧的一行短剧提示语，可选用于概括核心冲突或亮点，也可用作免责声明；不得超过 20 个字。 |
| `edit_param.template_edit.template` | - | string | 否 | "热门短剧1" | 枚举: ["热门短剧1","热门短剧2","热门短剧3","热门短剧4","热门短剧5"] | 默认为 热门短剧1；决定剧名、角标和提示语的位置及样式；支持 热门短剧1、热门短剧2、热门短剧3、热门短剧4、热门短剧5。 |
| `edit_param.template_edit.title` | - | string | 否 | - | 最长长度: 22 | 展示在解说视频画面上的短剧名称，用于品牌识别和引导用户搜索；不得超过 22 个字。 |
| `enable_return_poster` | `--enable-return-poster` | boolean | 否 | false | - | 默认为 false；true 会在任务结果中返回 poster_url，false 不返回封面图。 |
| `max_count` | `--max-count` | integer | 否 | 3 | 最小值: 1；最大值: 100 | 单次任务期望生成的解说视频数量上限，最小值为 1，不得超过 100，默认为 3。 |
| `max_duration` | `--max-duration` | number | 否 | 180 | 最小值: 1；最大值: 7200 | 每个解说视频的时长上限，单位为秒，最小值为 1，最大值为 7200，默认为 180 秒。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的火山引擎视频点播（VOD）空间或对象存储（TOS）桶：存储至 VOD 时设为 vod://<您的空间名>；存储至 TOS 时设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 vod:// 或 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要按需授权 AI MediaKit 将文件写入您的 VOD 空间或 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `min_duration` | `--min-duration` | number | 否 | 30 | 最小值: 1；最大值: 7200 | 每个解说视频的时长下限，单位为秒，最小值为 1，最大值为 7200，默认为 30 秒。 |
| `mode` | `--mode` | string | 否 | "text" | 枚举: ["narrate","text"] | 默认为 text；支持 narrate 和 text 两种模式。narrate 生成原片高光混剪、AI 语音解说和 BGM；text 生成原片高光混剪与屏幕文字解说。 |
| `narrate_bgm_url` | `--narrate-bgm-url` | string | 否 | - | - | 指定旁白解说模式下使用的背景音乐音频 URL；仅支持公网可访问的 HTTP/HTTPS URL；支持 mp3、m4a、wav 等主流音频格式；可选，不传时生成的解说视频不添加背景音乐。 |
| `narrate_options` | `--narrate-options` | object | 否 | - | - | 仅当 mode 为 narrate 时生效。 |
| `narrate_options.enable_narrate_bgm` | - | boolean | 否 | true | - | 默认为 true；true 启用 BGM 并使用 narrate_bgm_url 指定的音频，false 关闭背景音乐。 |
| `narrate_options.erase_subtitle_mode` | - | string | 否 | "mosaic" | 枚举: ["mosaic","standard"] | 默认为 mosaic；支持 mosaic 和 standard。mosaic 直接高斯模糊遮盖字幕区域，处理效率最高，适合快速遮挡且画面完整性要求不高的场景；standard 平衡擦除效果与效率，对纯色或简单背景效果良好，但复杂纹理或剧烈运动背景可能残留轻微涂抹痕迹。 |
| `narrate_options.narrate_ratio` | - | number | 否 | 0.3 | 最小值: 0；最大值: 1 | 控制旁白解说时长占生成视频时长的比例，最小值为 0，最大值为 1，默认为 0.3，建议不超过 0.5。 |
| `opening_hook` | `--opening-hook` | string | 否 | "auto" | 枚举: ["auto","force","disable"] | 精彩片段前置策略默认为 auto；支持 auto、force 和 disable。auto 会智能判断是否将最精彩片段前置到视频开头，force 强制开启精彩前置，disable 关闭精彩前置。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `text_options` | `--text-options` | object | 否 | - | - | 仅当 mode 为 text 时生效。 |
| `text_options.align_type` | - | string | 否 | "left" | 枚举: ["left","middle","right"] | 默认为 left；支持 left、middle、right，分别表示左对齐、居中对齐和右对齐。 |
| `text_options.border_color` | - | string | 否 | "#00000080" | 格式: "^#[0-9A-Fa-f]{8}$" | 花字描边颜色必须使用 #RRGGBBAA 格式，默认为 #00000080。 |
| `text_options.border_width` | - | integer | 否 | 2 | 最小值: 1 | 花字描边宽度单位为 px，默认为 2，建议不超过字号的 0.1 倍。 |
| `text_options.font_color` | - | string | 否 | "#FFFFF290" | 格式: "^#[0-9A-Fa-f]{8}$" | 花字颜色必须使用 #RRGGBBAA 格式，默认为 #FFFFF290。 |
| `text_options.font_size` | - | integer | 否 | - | 最小值: 1 | 花字字号单位为 px；未传时按视频短边除以 24 自动计算，例如 720p 默认 30、1080p 默认 45；不得小于 1。 |
| `text_options.font_type` | - | string | 否 | "SY_Bold" | 枚举: ["SY_Bold","SY_Black"] | 默认为 SY_Bold；支持 SY_Bold 和 SY_Black，分别表示思源粗体和思源黑体。 |
| `text_options.inner_padding` | - | integer | 否 | 1 | 最小值: 0 | 花字内边距单位为 px，默认为 1。 |
| `text_options.is_bold` | - | boolean | 否 | false | - | 花字是否加粗，默认为 false。 |
| `text_options.is_italic` | - | boolean | 否 | true | - | 花字是否斜体，默认为 true。 |
| `text_options.is_underline` | - | boolean | 否 | false | - | 花字是否添加下划线，默认为 false。 |
| `text_options.shadow_color` | - | string | 否 | "#00000080" | 格式: "^#[0-9A-Fa-f]{8}$" | 花字阴影颜色必须使用 #RRGGBBAA 格式，默认为 #00000080。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 30 | 待处理短剧原片的视频源 URL 列表；支持公网 HTTP/HTTPS、本地文件路径、视频点播 vod:// 和对象存储 tos:// 四类协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；单次任务支持传入 1 到 30 个视频文件；累计时长不得超过 120 分钟，即 2 小时；输入分辨率当前仅支持 1080p；输入素材需保持分辨率一致，否则会有兼容性问题；每个输入视频必须同时包含视频流和音频流；音频轨道必须包含清晰可识别的中文对话文本，仅含 BGM、纯音乐或语气词无法准确还原剧情；建议视频画面下半部分包含清晰居中的中文字幕，以提升文字解说定位和剧情理解准确度。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.input_duration` | number | 否 | Cloud 终态 | 输入视频总时长，单位为秒。 |
| `result.mode` | string | 否 | Cloud 终态 | 解说视频模式。 |
| `result.output_duration` | number / null | 否 | Cloud 终态 | 所有输出解说视频的总时长，单位为秒。 |
| `result.video_infos` | array<object> | 否 | Cloud 终态 | 每个解说视频的详细信息列表，并与 video_urls 顺序一致。 |
| `result.video_infos[].duration` | number / null | 否 | Cloud 终态 | 该条解说视频的时长，单位为秒。 |
| `result.video_infos[].poster_url` | string | 否 | Cloud 终态 | 未生成封面图或 enable_return_poster 为 false 时，poster_url 为空字符串。 |
| `result.video_infos[].size` | integer / string / null | 否 | Cloud 终态 | 该条解说视频的文件大小，单位为字节。 |
| `result.video_infos[].video_url` | string | 否 | Cloud 终态 | 设置 media_output_destination 后，返回 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key> 格式的存储地址；未设置 media_output_destination 时，返回有效期 24 小时的 HTTPS 临时下载链接。 |
| `result.video_urls` | array<string> | 否 | Cloud 终态 | 设置 media_output_destination 后，video_urls 返回 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key> 格式的存储地址；未设置 media_output_destination 时，video_urls 返回有效期 24 小时的 HTTPS 临时下载链接。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video drama-recap-vertical --help
mediakit-cli video drama-recap-vertical --schema
```
