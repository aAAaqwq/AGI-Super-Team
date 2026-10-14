# 搜狐视频解析与下载


## 支持输入

- `https://tv.sohu.com/v/<encoded_path>.html`
- `https://tv.sohu.com/<date>/<video_path>.shtml`
- `https://my.tv.sohu.com/us/<user_id>/<video_id>.shtml`
- 包含上述 URL 的分享文本

匿名稳定性以搜狐自媒体公开视频相对更好。电视剧、电影、会员、付费、地区限制和 DRM 内容不在候选范围内。

## 依赖和匿名边界

- Python 3.10+
- `yt-dlp`
- PyAV 可选，用于实际分辨率和完整时长校验

脚本不加载浏览器 Cookie、账号或用户 yt-dlp 配置。默认最多尝试 3 次，遇到首次完整成功立即结束。

## 实现说明

1. 只接受 `Sohu` / `SohuV` extractor。
2. 某些页面只暴露一个未标宽高的 MP4；下载后用 PyAV 补充实际分辨率。
3. 默认选择最低可用格式。只有一个格式时，分辨率范围以下载后探测值为准。
4. 429、页面结构失配和视频路径提取失败都保留为结构化错误，不伪造直链。

## 命令

```bash
python3 scripts/downloader/sohu_downloader.py --check --json
```

```bash
python3 scripts/downloader/sohu_downloader.py \
  "<sohu_video_url>" \
  --quality lowest \
  --print-url \
  --json
```

```bash
python3 scripts/downloader/sohu_downloader.py \
  "<sohu_video_url>" \
  --quality lowest \
  --attempts 3 \
  --output-dir downloads \
  --json
```

## 已观察结果

- 三个匿名公开样本中，第一个返回 HTTP 429，第二个无法提取视频路径，第三个完整下载成功。
- 成功样本为搜狐自媒体页面，只暴露一个 MP4。
- 实际文件为 848×480、含音频，时长约 213 秒。

因此搜狐应保持“已接入但仍不稳定”，不能因一次成功声明全站支持。

## 故障处理

- HTTP 429：停止高频请求并等待，不要并发重试。
- `Unable to extract video path`：页面结构或旧 URL 可能失效。
- 电视剧/电影页面只有受保护格式：匿名模式不支持。
- 下载 URL 带时效参数：解析后立即使用，不要缓存。

