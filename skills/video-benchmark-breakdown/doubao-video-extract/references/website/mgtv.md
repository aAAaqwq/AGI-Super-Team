# 芒果 TV 解析与下载


## 支持输入

- `https://www.mgtv.com/b/<collection_id>/<video_id>.html`
- `https://w.mgtv.com/b/<collection_id>/<video_id>.html`
- 包含上述 URL 的分享文本

仅面向公开可播放的花絮、片段或节目。会员、付费、地区限制、下架及 DRM 内容不在候选范围内。

## 依赖和匿名边界

- Python 3.10+
- `yt-dlp`
- PyAV 可选，用于完整时长和媒体流校验

脚本忽略本机 yt-dlp 配置，不读取浏览器 Cookie，不接受登录凭证。默认选择最低档并最多尝试 3 次，成功后立即停止。

## 实现说明

1. 仅接受 `MGTV` / `MangoTV` extractor。
2. 从 `format_note` 解析 `480P`、`576P`、`720P` 等清晰度标签。
3. 默认下载最低档；不假设标签与编码后的实际像素尺寸完全一致。
4. 下载后用 PyAV 反查实际宽高、时长和音频流。

## 命令

```bash
python3 scripts/downloader/mgtv_downloader.py --check --json
```

```bash
python3 scripts/downloader/mgtv_downloader.py \
  "<mgtv_video_url>" \
  --quality lowest \
  --print-url \
  --json
```

```bash
python3 scripts/downloader/mgtv_downloader.py \
  "<mgtv_video_url>" \
  --quality lowest \
  --attempts 3 \
  --output-dir downloads \
  --json
```

## 已观察结果

- 公开视频样本匿名完整下载成功。
- extractor 暴露 480P、576P、720P。
- 最低档标记为 480P，实际文件为 832×468、含音频，时长约 44 秒。

报告时同时保留平台标签和实际探测尺寸，不要把 480P 标签改写成精确的 832×480。

## 故障处理

- `No video formats found`：页面可能下架、权限受限或 extractor 失配。
- HLS 临时 URL 过期：重新解析并下载，不要复用旧 URL。
- 会员或 DRM 内容：匿名下载器不支持，不要读取浏览器 Cookie。
- 页面标题可能只返回节目名而非片段标题；字段以 yt-dlp 实际结果为准。

