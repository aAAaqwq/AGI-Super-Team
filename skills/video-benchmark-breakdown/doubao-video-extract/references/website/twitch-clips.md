# Twitch Clips 视频解析与下载


## 支持输入

- `clips.twitch.tv/<clip_slug>`
- `twitch.tv/<channel>/clip/<clip_slug>`
- 包含上述完整链接的分享文本

当前只覆盖 Clips，不支持直播、VOD、合集、频道页、订阅者专享或登录后内容。

## 依赖

- Python 3.10 或更高版本
- `yt-dlp`
- `scripts/downloader/yt_dlp_candidate_common.py`

脚本只检查依赖，不会自动安装或升级，也不会读取浏览器 Cookie。

## 实现说明

下载器使用 `yt-dlp` 的 `TwitchClips` extractor：

1. 从输入或分享文本提取首个 URL。
2. 严格校验 URL 是 `clips.twitch.tv` 或频道 Clip 页面。
3. 使用 `--no-config --no-playlist`，不读取用户配置，不传账号、Cookie 或 Token。
4. 解析模式使用 `--skip-download --dump-single-json`。
5. 下载模式使用 `yt-dlp` 选择格式并保存文件。
6. 下载完成后检查文件存在且非空。

## 预检命令

```bash
python3 scripts/downloader/twitch_clips_downloader.py --check --json
```

## 解析命令

```bash
python3 scripts/downloader/twitch_clips_downloader.py \
  "<twitch_clip_url_or_share_text>" \
  --print-url \
  --json
```

## 下载命令

```bash
python3 scripts/downloader/twitch_clips_downloader.py \
  "<twitch_clip_url_or_share_text>" \
  --output-dir downloads \
  --json
```

可以用 `--format "<yt_dlp_format_selector>"` 覆盖默认的 `best`。

## 输出字段

基础字段：

- `platform`：固定为 `twitch_clips`
- `video_url`
- `file_path`（下载模式）
- `video_id`
- `page_url`
- `format_id`
- `quality`

`metadata` 中按实际返回保留：

- 标题、描述
- 主播、频道及 ID
- 时长、发布时间
- 封面、播放统计
- 可用格式及宽高、帧率、编码、大小

字段拿不到时省略，不要编造。

## 故障处理

- `KeyError('data')` 或 extractor error：先确认 `yt-dlp` 已升级，再用同一 Clip URL 重试一次。
- Clip 已删除、仅订阅者可见或要求登录：停止并报告限制，不要要求用户粘贴 Cookie。
- 输入是直播或 VOD：不属于本下载器支持范围。
- HTTP 403/429：停止高频重试，等待平台限制解除。
- 临时媒体 URL 失效：重新执行完整解析或下载命令，不要长期缓存。

## 文本提取边界

本 reference 只负责 Clip 媒体和元数据。通过统一入口处理文本时，字幕、逐字稿、总结和时间轴仍使用现有飞书妙记链路。

## 集成状态

- 下载器和共享适配器已进入 `scripts/downloader/`。
- 统一入口仅识别 Clips，明确排除 Twitch VOD 和直播。
- 本次融合未重新执行 Twitch 联网下载；网络可达性和 extractor 兼容性仍以运行时结果为准。
