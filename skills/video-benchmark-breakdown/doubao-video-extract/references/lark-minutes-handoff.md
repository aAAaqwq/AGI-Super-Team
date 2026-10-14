# 飞书妙记交接

当在线视频或本地视频需要生成脚本、字幕、摘要、章节或关键词时，使用本参考。

如果输入是在线视频网站链接，不要先单独下载视频；本参考使用统一入口完成下载、转音频、上传飞书妙记和读取产物。在线链接必须成功转换为音频后才能上传，禁止上传视频文件。只有用户提供本地文件时才能上传视频文件。

文本、原文、关键词、时间轴和口播内容必须来自本参考生成的妙记产物。禁止用浏览器打开视频页后通过页面搜索、站内搜索、评论/标题/描述检索、字幕面板或网页 OCR 结果来替代 `--run-lark`。

## 飞书 Skill 参考

正常执行不需要预读飞书 Skill。优先使用统一入口：

```bash
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --run-lark
```

只有在统一入口返回授权、权限、上传、妙记或 `vc +notes` 问题，且错误信息不足以判断时，再读取相关飞书 Skill 排障。

## 工作流

1. 在线链接直接运行 `python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --run-lark`；本地文件可跳过下载。
2. 在线链接必须用 PyAV 转成音频；转换失败时停止，不得回退上传源视频。本地文件可选择上传转换后的音频或原视频。
3. 用 `lark-cli drive +upload --file <relative_path> --format json` 上传媒体文件。
4. 从云空间返回值中提取 `file_token`。
5. 用 `lark-cli minutes +upload --file-token <file_token> --format json` 生成妙记。
6. 从返回的 `minute_url` 中提取 `minute_token`。
7. 用 `lark-cli vc +notes --minute-tokens <minute_token> --output-dir minutes --format json` 读取产物。
8. 如果飞书返回 `minute not ready`，等待后重试。

实现注意：
- 从媒体文件所在目录执行云空间上传，并传入 `./filename`；`lark-cli` 会拒绝绝对路径和 cwd 外部路径。
- `vc +notes` 返回 `minute not ready` 时继续轮询；helper 默认重试 10 次，每次等待 60 秒。等待估算以脚本输出为准，不要手算。
- 音频模式默认使用 PyAV 生成 MP3。
- 如果 PyAV 转换失败，在线来源会停止并拒绝上传视频；只有本地文件可以记录 `audio_fallback_reason` 并回退上传源视频。

## Helper 行为
- 在线网站识别、短链规范化、平台 downloader 选择、下载命令和元数据返回规则见 `references/website_extract.md`。
- 默认下载目录请求为 `./downloads`；若该目录不可写，下载器可回退到用户缓存目录。
- 默认音频格式是 `mp3`，音频转换只使用 PyAV；未指定 `--audio-output-dir` 时，音频保存在下载器实际返回的视频目录中，避免下载目录回退后路径不一致。需要 WAV 时显式传 `--audio-format wav`。在线来源不得使用 `--media-mode video --run-lark`。
- 音频转换失败时，读取错误中的异常类型和具体路径；不要仅凭 `--check` 中 PyAV 可用就推断转换一定成功。
- 当飞书返回 `minute not ready` 时，helper 默认最多轮询 10 次，每次间隔 30 秒。默认轮询窗口是脚本等待上限，不代表妙记一定处理完成；具体预估等待时间和超时时间读取 `lark_result.wait_estimate`。
- 如果本地已经存在 `transcript.txt`，helper 返回 `status: "processing_with_transcript"`、`ready_state: "processing"` 和 `transcript_file`，可把该 transcript 作为当前结果使用。
- 当找到 `transcript.txt` 时，helper 默认生成豆包文档格式 Markdown 产物 `doubao_transcript.md`，并在结果中返回 `doubao_doc_file`。

## 飞书妙记耗时

不要让模型自行估算处理时间。使用统一入口返回的 `lark_result.wait_estimate`，或直接调用估算脚本：

```bash
python3 scripts/minutes/estimate_lark_minutes_wait.py --media "<media_file>"
```

脚本输出包含：

- `estimated_processing_seconds` / `estimated_processing_human`：预估处理时间。
- `timeout_seconds` / `timeout_human`：建议报告明显超时的时间。
- `helper_poll_seconds` / `helper_poll_human`：helper 本次最多等待的轮询窗口。

明显超时时，向用户报告实际等待时长、`wait_estimate` 和 `minute_token`，让用户决定继续等待还是重试。


## Helper 命令

```bash
# 默认路径：用 PyAV 抽 MP3 音频后上传，并执行飞书链路。
python3 scripts/minutes/social_video_to_minutes.py "<url>" --run-lark

# 如需 WAV 音频，显式指定格式。
python3 scripts/minutes/social_video_to_minutes.py "<url>" --run-lark --audio-format wav

# 只有本地文件可以跳过音频抽取，直接上传视频。
python3 scripts/minutes/social_video_to_minutes.py "/path/to/local-video.mp4" --media-mode video --run-lark
```

报告结果时包含保存后的 MP4 路径、使用到的音频路径、`minute_url`、`minute_token`、脚本产物路径和 `doubao_doc_file`。用户要求脚本或逐字稿时，默认交付 `doubao_doc_file`。

不要先运行 `--media-mode video` 再运行 `--run-lark`。文本提取任务直接运行 `--run-lark`。
