# X 视频解析与下载

## 支持输入

- 公开的 `x.com/<user>/status/<status_id>` 视频帖子
- 兼容的 `twitter.com/<user>/status/<status_id>` 历史链接
- 包含上述完整链接的分享文本

当前不支持纯图文帖子、账号主页、搜索页、Spaces、直播、私密帖子、删除内容、年龄限制、地区限制或登录后才可访问的内容。

## 依赖

- Python 3.10 或更高版本
- `yt-dlp`
- `scripts/downloader/yt_dlp_candidate_common.py`

脚本只检查依赖，不会自动安装或升级，也不会读取浏览器 Cookie。

## 实现说明

下载器使用 `yt-dlp` 的 `Twitter` extractor：

1. 从输入或分享文本提取首个 URL。
2. 严格校验 URL 是 X/Twitter 的状态详情页。
3. 使用 `--no-config --no-playlist`，不读取用户配置，不传账号、Cookie 或 Token。
4. 解析模式使用 `--skip-download --dump-single-json`。
5. 下载模式由 `yt-dlp` 完成，并验证文件存在且非空。
6. 输出只保留结构化字段，不透传 extractor 返回的 Cookie、请求头或其他会话数据。

## 预检命令

```bash
python3 scripts/downloader/x_downloader.py --check --json
```

## 解析命令

```bash
python3 scripts/downloader/x_downloader.py \
  "<x_status_url_or_share_text>" \
  --print-url \
  --json
```

## 下载命令

```bash
python3 scripts/downloader/x_downloader.py \
  "<x_status_url_or_share_text>" \
  --output-dir downloads \
  --json
```

可以用 `--format "<yt_dlp_format_selector>"` 覆盖默认的 `best`。

## 输出字段

基础字段：

- `platform`：固定为 `x`
- `video_url`
- `file_path`（下载模式）
- `video_id`
- `page_url`
- `format_id`
- `quality`

`metadata` 中按实际返回保留：

- 标题、描述
- 作者、作者 ID
- 时长、发布时间
- 封面
- 播放、点赞、评论、转发统计
- 可用格式及宽高、编码、大小

字段拿不到时省略，不要编造。

## 故障处理

- 帖子不含视频：不属于本下载器支持范围。
- HTTP 401/403/429：停止高频重试，报告登录、风控、地区或限流限制。
- 私密、删除或登录后帖子：不要改用浏览器 Cookie 绕过。
- 返回媒体 URL 但下载失败：临时签名可能过期，重新运行完整命令解析，不要长期缓存直链。
- 下载完成但文件为空：保留错误，不要把临时文件当作成功产物。

## 文本提取边界

本 reference 只负责 X 帖子中的视频媒体和元数据。通过统一入口处理文本时，字幕、逐字稿、总结和时间轴仍使用现有飞书妙记链路。
