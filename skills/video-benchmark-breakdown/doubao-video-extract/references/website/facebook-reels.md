# Facebook Reels 视频解析与下载


## 命名

Meta 是公司品牌，Facebook 仍是产品、域名和 `yt-dlp` extractor 名称。本实现能力应写作 `Facebook Reels（Meta 旗下）`，不要写成 `Meta Video`。

## 支持输入

- 公开的 `facebook.com/reel/<reel_id>` 页面
- 移动站 `m.facebook.com/reel/<reel_id>` 页面
- 包含上述完整链接的分享文本

当前只覆盖 Reels，不支持普通 Facebook Video 页面、帖子页、Watch 页面、`fb.watch` 短链、私密内容或登录后内容。

## 依赖

- Python 3.10 或更高版本
- `yt-dlp`
- `scripts/downloader/yt_dlp_candidate_common.py`

脚本只检查依赖，不会自动安装或升级，也不会读取浏览器 Cookie。

## 实现说明

下载器使用 `yt-dlp` 的 Facebook extractor，但在入口层只接受 `/reel/<id>`：

1. 从输入或分享文本提取首个 URL。
2. 严格校验 URL 是 Facebook Reel 页面。
3. 使用 `--no-config --no-playlist`，不读取用户配置，不传账号、Cookie 或 Token。
4. 解析模式使用 `--skip-download --dump-single-json`。
5. 下载完成后检查文件存在且非空。
6. 输出不会包含 extractor 内部 Cookie 或请求头。

## 预检命令

```bash
python3 scripts/downloader/facebook_reels_downloader.py --check --json
```

## 解析命令

```bash
python3 scripts/downloader/facebook_reels_downloader.py \
  "<facebook_reel_url_or_share_text>" \
  --print-url \
  --json
```

## 下载命令

```bash
python3 scripts/downloader/facebook_reels_downloader.py \
  "<facebook_reel_url_or_share_text>" \
  --output-dir downloads \
  --json
```

可以用 `--format "<yt_dlp_format_selector>"` 覆盖默认的 `best`。

## 输出字段

基础字段：

- `platform`：固定为 `facebook_reels`
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
- 封面、播放和互动统计
- 可用格式及宽高、编码、大小

字段拿不到时省略，不要编造。

## 故障处理

- `Cannot parse data`：先确认输入确实是 `/reel/<id>`，普通 Facebook Video 当前不在支持范围。
- 登录页、私密帖子、地区限制或删除内容：停止并报告限制，不要要求用户粘贴 Cookie。
- `fb.watch` 短链：当前不接受；先补短链展开和回归测试，再扩大支持范围。
- HTTP 403/429：停止高频重试，等待平台限制解除。
- 临时媒体 URL 失效：重新运行完整命令，不要长期缓存。

## 文本提取边界

本 reference 只负责 Reel 媒体和元数据。通过统一入口处理文本时，字幕、逐字稿、总结和时间轴仍使用现有飞书妙记链路。

## 集成状态

- 下载器和共享适配器已进入 `scripts/downloader/`。
- 统一入口只识别 Facebook Reels，不会把普通 Facebook Video 页面误路由为 Reel。
- 本次融合未重新执行 Facebook 联网下载；平台风控和地区可达性仍以运行时结果为准。
