# TikTok 视频解析与下载


## 支持输入

- 公开的 `tiktok.com/@<user>/video/<video_id>` 页面
- 包含上述完整链接的分享文本

当前不接受 `vm.tiktok.com`、`vt.tiktok.com` 等短链，也不支持账号主页、合集、直播、私密、删除、登录后或地区受限内容。

## 依赖

- Python 3.10 或更高版本
- `yt-dlp`
- `curl-cffi` impersonation 支持
- `scripts/downloader/yt_dlp_candidate_common.py`

建议由开发者在脚本外安装：

```bash
uv tool install --upgrade "yt-dlp[default,curl-cffi]"
```

脚本不会自动安装或升级依赖，也不会读取浏览器 Cookie。

## 实现说明

普通匿名请求可能返回 `Unexpected response from webpage request`。下载器默认追加：

```text
--impersonate chrome
```

`chrome` 是 `yt-dlp` 的通用选择器，会从当前 `curl-cffi` 支持的目标中选择 Chrome，不写死具体浏览器版本。

处理流程：

1. 从输入或分享文本提取首个 URL。
2. 严格校验 URL 是完整 TikTok 单视频页面。
3. 使用 `--no-config --no-playlist`，不读取用户配置，不传账号、用户 Cookie 或 Token。
4. 使用 Chrome TLS impersonation 建立匿名网页会话。
5. 解析模式使用 `--skip-download --dump-single-json`。
6. 下载完成后检查文件存在且非空。
7. 输出不会包含 extractor 内部生成的匿名会话 Cookie、请求头或临时调试数据。

## 预检命令

```bash
python3 scripts/downloader/tiktok_downloader.py --check --json
```

预检结果中的 `impersonation_available` 应为 `true`。

## 解析命令

```bash
python3 scripts/downloader/tiktok_downloader.py \
  "<tiktok_video_url_or_share_text>" \
  --print-url \
  --json
```

## 下载命令

```bash
python3 scripts/downloader/tiktok_downloader.py \
  "<tiktok_video_url_or_share_text>" \
  --output-dir downloads \
  --json
```

可以用 `--format "<yt_dlp_format_selector>"` 覆盖默认的 `best`，也可以用 `--impersonate "<client[:os]>"` 覆盖默认的 `chrome`。

## 输出字段

基础字段：

- `platform`：固定为 `tiktok`
- `video_url`
- `file_path`（下载模式）
- `video_id`
- `page_url`
- `format_id`
- `quality`

`metadata` 中按实际返回保留：

- 标题、描述
- 作者、作者 ID、频道
- 音轨、艺术家
- 时长、发布时间
- 封面
- 播放、点赞、评论、转发统计
- 可用格式及宽高、编码、大小

字段拿不到时省略，不要编造。

## 故障处理

- `Unexpected response from webpage request`：确认 `curl-cffi` 已安装，预检中存在 Chrome impersonation target。
- `Your IP address is blocked`：停止重试并报告出口 IP 限制，不要切换到用户登录态。
- HTTP 403/429：停止高频重试，等待平台限制解除。
- 短链输入：当前不支持；补短链展开和真实回归测试后再扩大范围。
- 临时媒体 URL 失效：重新执行完整命令，不要长期缓存带签名 URL。
- 登录、私密、删除或地区限制：停止并返回结构化限制。

## 文本提取边界

本 reference 只负责视频媒体和元数据。通过统一入口处理文本时，字幕、逐字稿、总结和时间轴仍使用现有飞书妙记链路。

## 集成状态

- 下载器和共享适配器已进入 `scripts/downloader/`。
- 统一入口识别完整 TikTok 视频页；短链仍未接入。
- 本次融合未重新执行 TikTok 联网下载；IP、地区、风控和格式可用性仍以运行时结果为准。
