# YouTube 视频解析与下载

当前实现严格限定为公开的 `youtube.com/watch?v=<video_id>` 单视频页面。

## 支持输入

- 支持公开的 `youtube.com/watch?v=<video_id>` 页面。
- 支持包含上述完整链接的分享文本。
- 不支持 `youtu.be` 短链、Shorts、播放列表和直播回放。
- 不支持需要登录、会员、年龄验证、地区权限或已删除、私密的视频。

## 依赖

- Python 3.10 或更高版本。
- 当前 Python 环境或 `PATH` 中可调用的 `yt-dlp`。

运行时只检查依赖，不会自动安装或升级：

```bash
python3 scripts/downloader/youtube_downloader.py --check --json
```

## 实现说明

实现来自 `tmp/youtube/` 记录的真实样例实验，使用 `yt-dlp` 的 Android player client：

1. 规范化输入并严格校验 `youtube.com/watch` 和 11 位视频 ID。
2. 使用 `--no-config --no-playlist`，不读取用户配置、浏览器 Cookie、账号或 PO Token。
3. 读取 Android client 返回的实际格式。
4. 优先选择已验证的 format `18`，即通常为 640×360、H.264 + AAC 的音视频合一 MP4。
5. format `18` 不存在时，只选择实际返回的、同时包含音视频的最高质量 MP4。
6. 如果只剩音视频分离格式，停止并报告；不猜固定 ID，也不引入外部媒体合并器。媒体处理仍统一使用 PyAV。
7. 下载完成后检查最终文件存在且非空。

Android client 仍可能警告其他 HTTPS 格式需要 GVS PO Token。只要实际存在可下载的音视频合一 MP4，该警告不等同于失败；如果只剩 storyboard、音视频分离格式或下载返回 403，则视为当前不可用。

不要把 PO Token、Cookie 或登录凭证写入代码、命令、日志或 reference。

## 解析命令

读取元数据和当前选中的临时媒体 URL，不下载：

```bash
python3 scripts/downloader/youtube_downloader.py \
  "<youtube_watch_url_or_share_text>" \
  --print-url \
  --json
```

## 下载命令

```bash
python3 scripts/downloader/youtube_downloader.py \
  "<youtube_watch_url_or_share_text>" \
  --output-dir downloads \
  --json
```

也可以使用统一入口：

```bash
python3 scripts/minutes/social_video_to_minutes.py \
  "<youtube_watch_url_or_share_text>" \
  --media-mode video
```

长视频下载可能持续较久。调用方应等待进程完成并检查退出码，再检查输出文件存在且非空；不要把“开始下载”当成成功。

## 输出字段

基础字段：

- `platform`
- `video_url`
- `file_path`（下载模式）
- `video_id`
- `page_url`
- `format_id`
- `quality`
- `selected_format`

`metadata` 中按实际返回保留：

- 标题、描述
- 作者、作者 ID、频道、频道 ID
- 封面
- 时长、发布时间
- 播放量、点赞量、评论量
- 章节
- 可用格式列表

字段拿不到时省略，不要编造。不要长期保存带时效签名的临时媒体 URL。

## 文本提取边界

本 reference 只负责 MP4 和元数据。即使 `yt-dlp` 能读取 YouTube 自动字幕，也不要直接把平台字幕接入正式文本产物：

- 原验证中英文自动字幕可用，但简体中文字幕请求曾返回 `HTTP 429`。
- 平台字幕的语言、完整性、限流和可用性需要独立回归。
- 字幕、逐字稿、总结和时间轴仍使用现有飞书妙记链路。

## 故障处理

- `The page needs to be reloaded` 或 SABR 提示：确认下载器使用 Android client。
- format `18` 不存在：允许下载器从实际格式中选择其他音视频合一 MP4，不要假设 format `18` 永远存在。
- 只有音视频分离格式或 storyboard：当前无可用的音视频合一 MP4，停止并报告。
- HTTP 403：重新解析一次；仍失败则返回结构化限制，不要伪造成功。
- HTTP 429：停止高频重试并退避。
- 登录、会员、年龄、地区、私密或删除限制：不要要求用户粘贴 Cookie、Token 或账号凭证。

## 已验证案例

- 页面：`https://www.youtube.com/watch?v=yhn501096Fc`
- player client：`android`
- format：`18`
- 文件：MP4，640×360，H.264 + AAC
- 原实验结果：约 27 MB，下载进程退出码 0
- 元数据：标题、858 秒时长、作者、频道、播放量、点赞量、发布日期、描述、章节
- 原验证来源：2026-07-30 自动 trace 报告
