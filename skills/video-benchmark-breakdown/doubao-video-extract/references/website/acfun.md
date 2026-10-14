# AcFun 视频解析与下载


## 支持输入

- `https://www.acfun.cn/v/ac<content_id>`
- 带分 P 后缀或 query 的公开 AcFun 视频页
- 包含 AcFun 视频 URL 的分享文本

当前候选只启用 `AcFunVideo`，不声明支持番剧、会员、地区限制、私密或已删除内容。

## 依赖和匿名边界

- Python 3.10+
- `yt-dlp`
- PyAV 可选，用于媒体完整性验证

脚本始终忽略 yt-dlp 用户配置，不读取 Cookie 或登录凭证。默认选择最低分辨率并最多尝试 3 次。

## 实现说明

1. 使用 `AcFunVideo` extractor 枚举公开 HLS/MP4 格式。
2. 横屏和竖屏视频都按实际像素面积选择最低档。
3. JSON 同时输出 `available_resolutions` 和 `resolution_range`，避免只用高度描述竖屏视频。
4. 下载完成后验证首帧、音频和实际时长；不足页面时长 90% 的文件视为不完整。

## 命令

```bash
python3 scripts/downloader/acfun_downloader.py --check --json
```

```bash
python3 scripts/downloader/acfun_downloader.py \
  "<acfun_video_url>" \
  --quality lowest \
  --print-url \
  --json
```

```bash
python3 scripts/downloader/acfun_downloader.py \
  "<acfun_video_url>" \
  --quality lowest \
  --attempts 3 \
  --output-dir downloads \
  --json
```

## 已观察结果

- 公开 UGC 样本匿名完整下载成功。
- 竖屏样本暴露 360×640、540×960、720×1280、1080×1920。
- 最低档实际为 360×640、含音频，时长约 174 秒。
- 另一个横屏页面曾直接暴露 360P、540P、720P 的未加密 HLS。

## 故障处理

- 404：视频、分 P 或旧测试 ID 已失效。
- 只有番剧 extractor 可匹配：当前脚本拒绝，避免扩大到授权内容。
- HLS 下载失败：重新解析临时 URL；不要手工拼 CDN 参数。
- 竖屏视频的 `height` 大于 `width` 是正常结果，不要把 360×640 误报为 640P 横屏。

