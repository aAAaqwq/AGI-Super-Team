# 视频转码

## 能力用途

视频转码将视频码流转换为另一视频码流，可涉及编码格式、分辨率、码率、I 帧间隔和封装格式转换，用于适应不同业务场景、播放终端和网络环境。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video transcode-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 数组参数（`--metadata-keep-tags`）传多个值时用逗号分隔并整体加引号，例如 `--metadata-keep-tags "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--audio`、`--metadata-add-tags`、`--video`）需传合法 JSON 字符串并整体加单引号，例如 `--audio '[{...}]'`；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。
- 不要用逗号分隔或裸文本传该参数。

### 调用示例

```bash
mediakit-cli video transcode-video \
  --video-url <video_url> \
  --container-format <container_format> \
  --video <video>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio` | `--audio` | object | 否 | - | - | 不传 audio 时，音频使用 aac 编码，其他参数跟随源文件。 |
| `audio.bitrate_kbps` | - | integer | 是 | 128 | 最小值: 10；最大值: 500 | 音频码率单位 Kbps，范围 [10, 500]，默认 128；不设置时跟随原始音频码率。 |
| `audio.bitrate_mode` | - | string | 是 | "cbr" | 枚举: ["cbr","cae"] | cae 仅在 audio.codec=aac 时支持，按内容复杂度调整瞬时码率并使平均码率接近 bitrate_kbps。cbr 是默认恒定码率模式，仅在 video.codec=h264 时支持，用于带宽稳定性要求高的流式传输。 |
| `audio.channels` | - | integer | 否 | 2 | 枚举: [1,2] | 音频声道数支持 1（单声道）和 2（双声道），默认是 2。 |
| `audio.codec` | - | string | 是 | "aac" | 枚举: ["aac"] | 音频编码当前仅支持 aac，默认也是 aac。 |
| `audio.sample_rate` | - | integer | 是 | 44100 | 枚举: [8000,11025,12000,16000,22050,24000,32000,44100,48000,64000,88200,96000] | aac 支持采样率 8000、11025、12000、16000、22050、24000、32000、44100、48000、64000、88200、96000 Hz，默认 44100 Hz。 |
| `audio.volume_integrated_loudness` | - | number | 否 | -12 | 最小值: -70；最大值: -5 | 响度值设置，用于在音量均衡模式下调整音频的整体响度水平。取值范围为 [-70, -5]，默认值为 -12。当 Method 参数取值为 2Pass时，该参数必填。 |
| `audio.volume_loudness_range` | - | number | 否 | 7 | 最小值: 1；最大值: 20 | 响度范围单位 LU，范围 [1, 20]，默认 7；volume_method=2Pass 时生效。 |
| `audio.volume_method` | - | string | 否 | - | 枚举: ["2Pass"] | volume_method=2Pass 可启用两阶段响度分析与处理，使三个响度参数生效；不设置时不处理音量。 |
| `audio.volume_true_peak` | - | number | 否 | 0 | 最小值: -9；最大值: 0 | 音量峰值，用于在音量均衡模式下设置音频的最大峰值。取值范围为 [-9, 0]，默认值为 0。当 Method 参数取值为 2Pass时，该参数必填。 |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `container_format` | `--container-format` | string | 是 | "MP4" | 枚举: ["MP4","FLV","MPEGTS"] | 输出封装格式支持 MP4、FLV、MPEGTS，默认是 MP4。 |
| `media_output_destination` | `--media-output-destination` | string | 否 | - | - | 指定处理产物的目标存储位置。AI MediaKit 支持将处理产物存储至您的对象存储（TOS）桶，可设为 tos://<您的桶名>。设置后，任务结果中的 url 相关字段将返回 tos:// 格式的资源地址，不再返回临时下载地址。首次使用前，需要授权 AI MediaKit 将文件写入您的 TOS 桶。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `metadata_add_tags` | `--metadata-add-tags` | array<object> | 否 | - | - | 新增元信息标签与保留标签同名时，新设置覆盖源文件值。metadata_add_tags 对 MPEGTS 封装格式无效。 |
| `metadata_add_tags[].key` | - | string | 否 | - | - | 标签键。 |
| `metadata_add_tags[].value` | - | string | 否 | - | - | 标签值。 |
| `metadata_keep_tags` | `--metadata-keep-tags` | array<string> | 否 | - | - | 可指定从源视频保留的元信息标签键；默认转码会丢弃大部分元信息。metadata_keep_tags 对 MPEGTS 封装格式无效。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `video` | `--video` | object | 是 | - | - | 视频参数，必填 |
| `video.bitrate_crf` | - | number | 否 | 25 | 最小值: 0；最大值: 51 | bitrate_crf 仅在 bitrate_mode=crf 时生效；值越小画质越高、体积越大，0 表示无损。bitrate_crf 范围 [0, 51]。 |
| `video.bitrate_kbps` | - | integer | 是 | 2000 | 最小值: 10；最大值: 50000 | video.bitrate_kbps 在 crf、abr、cbr 模式下分别表示最大码率限制、平均码率目标、恒定码率目标。 |
| `video.bitrate_mode` | - | string | 是 | "crf" | 枚举: ["crf","abr","cbr"] | crf 推荐用于大多数场景，尽量保持 bitrate_crf 指定的视觉质量，并以 bitrate_kbps 限制瞬时码率。abr 调整码率使整体平均码率接近 bitrate_kbps，适合将文件大小控制在特定范围。cbr 尝试让视频流每秒严格保持 bitrate_kbps 设定码率，适合要求网络传输稳定的流媒体场景。 |
| `video.codec` | - | string | 是 | "h264" | 枚举: ["h264","h265"] | 视频编码格式支持 h264 和 h265，默认是 h264。 |
| `video.fps` | - | integer | 否 | - | 最小值: 1；最大值: 240 | fps 范围 [1, 240]；vfr 下是最大帧率，cfr 下是恒定帧率。 |
| `video.fps_mode` | - | string | 否 | "vfr" | 枚举: ["vfr","cfr"] | 只有设置 fps 后 fps_mode 才生效；未提供 fps 时遵循原视频帧率并忽略 fps_mode。cfr 将 fps 作为强制恒定输出帧率。vfr 将 fps 作为最高帧率；源帧率较低时保留，较高时降低到 fps。 |
| `video.is_hdr_to_sdr` | - | boolean | 否 | true | - | true 将 HDR 转换为 SDR；false 保留 HDR。 |
| `video.scale_height` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_height 单位为 px，范围 [0, 4320]，仅在 scale_type=2 时生效；只传宽或高之一时另一边按比例缩放。 |
| `video.scale_long` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_long 单位为 px，范围 [0, 4320]，仅在 scale_type=1 时生效；只传短边或长边之一时另一边按比例缩放。 |
| `video.scale_mode` | - | integer | 否 | 0 | 枚举: [0,1,2] | scale_mode 仅在 scale_type 为 1 或 2 时生效。0 不上采：源片大于目标时缩小，小于目标时保持原尺寸。1 强制拉伸到目标宽高，可能导致画面变形。2 等比缩放到目标框内并用黑边填充不足部分。 |
| `video.scale_short` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_short 单位为 px，范围 [0, 4320]，仅在 scale_type=1 时生效；只传短边或长边之一时另一边按比例缩放。 |
| `video.scale_type` | - | integer | 否 | 0 | 枚举: [0,1,2] | scale_type=0 跟随片源且不缩放，相关尺寸参数无效，最高支持 8K。scale_type=1 激活 scale_short 和 scale_long，另一边按原比例缩放，最高支持 4K。scale_type=2 激活 scale_width 和 scale_height，另一边按原比例缩放，最高支持 4K。视频缩放模式默认是 0。 |
| `video.scale_width` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_width 单位为 px，范围 [0, 4320]，仅在 scale_type=2 时生效；只传宽或高之一时另一边按比例缩放。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待转码视频支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式；支持公网 HTTP/HTTPS URL、本地文件路径、vod:// 和 tos:// 四种来源协议。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.duration` | number | 否 | Cloud 终态 | 转码后视频时长，单位为秒。 |
| `result.resolution` | string | 否 | Cloud 终态 | 转码后视频分辨率规格，可能包括 240p、360p、480p、540p、720p、1080p、2k、4k 等。 |
| `result.video_codec` | string | 否 | Cloud 终态 | 转码后视频的编码格式。 |
| `result.video_url` | string | 否 | Cloud 终态 | 未设置 media_output_destination 时返回有效期 24 小时的 HTTPS 临时下载链接；设置后返回 vod:// 或 tos:// 存储地址。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video transcode-video --help
mediakit-cli video transcode-video --schema
```
