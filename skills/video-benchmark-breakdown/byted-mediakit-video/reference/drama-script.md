# 剧本还原

## 能力用途

基于大模型视频理解能力，将短剧视频转化为结构化剧本文本，识别并提取场景、人物、对话和情节等核心元素。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video drama-script`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--return-pkg`）只能写成 `--return-pkg=true` 或 `--return-pkg=false`，也可用裸 `--return-pkg`（等价 true）；禁止空格传值 `--return-pkg true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。

### 调用示例

```bash
mediakit-cli video drama-script \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `callback_args` | `--callback-args` | string | 否 | - | - | 自定义回调参数。任务完成时，您提供的内容会通过事件回调原样返回，便于关联业务；字段长度最大为 512 字节。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `callback_url` | `--callback-url` | string | 否 | - | - | 用于接收该任务结果回调的 URL 地址。提供此参数时，其优先级高于全局回调地址；地址必须以 http:// 或 https:// 开头。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制。大小写敏感，不超过 64 个 ASCII 码可打印字符。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `queue_id` | `--queue-id` | string | 否 | - | - | 任务提交的目标队列 ID。如不传，默认使用系统自动创建的队列 ID。可将不同业务或优先级的任务提交到不同队列，以实现按队列对应的项目分账。队列可创建和管理，系统会自动为队列分配队列 ID。 仅在用户明确提供该值时传递；不得由 Agent 生成、推断或补写。 |
| `return_pkg` | `--return-pkg` | boolean | 否 | false | - | 控制任务结果的输出封装格式。true 时，所有任务产物会打包为 .tar.gz 压缩包，result_url 指向该压缩包，压缩包包含核心剧本 JSON、人物名及其图片、场景截图等分析结果；false 时，仅返回核心剧本数据，result_url 指向 Gzip 压缩的 JSON 文件 .json.gz。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 100 | 待处理短剧视频的 URL 列表。单次任务支持传入 1 个至 100 个视频文件，并按 video_urls 的数组顺序拼接视频后进行分析。视频输入支持公网 HTTP/HTTPS URL、本地文件路径、vod:// 和 tos:// 四种协议来源，也支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流格式；不支持 HLS（M3U8）格式。单个视频文件时长不超过 120 分钟，单次任务所有视频累计时长不超过 300 分钟，视频必须包含内嵌硬字幕。适用于以人物对话和情节发展为核心的真人实拍短剧、长剧和电影；不适用于缺乏连贯真人剧情或人脸识别线索的动画、纪录片、广告和直播录屏。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `result.drama_script_task_id` | string / null | 否 | Cloud 终态 | 剧本还原任务 ID。 |
| `result.duration` | number / null | 否 | Cloud 终态 | 输入视频总时长，单位为秒。 |
| `result.result_url` | string | 否 | Cloud 终态 | 最终生成的剧本文件下载地址，为公网 URL；有效期为 24 小时，务必及时保存。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video drama-script --help
mediakit-cli video drama-script --schema
```
