# 梨视频解析与下载


## 支持输入

- `https://www.pearvideo.com/video_<content_id>`
- `https://m.pearvideo.com/video_<content_id>`
- 包含上述 URL 的分享文本

仅支持仍公开可访问的梨视频详情页。删除、私密、下架或只在 App 中提供的内容不在候选范围内。

## 依赖和匿名边界

- Python 3.10+
- `yt-dlp`
- PyAV 可选，用于反查实际分辨率、时长和音频流

脚本不使用登录态、浏览器 Cookie 或用户 yt-dlp 配置。默认选择最低格式，最多尝试 3 次并在首次成功后停止。

## 实现说明

1. 仅接受 `PearVideo` extractor。
2. 梨视频当前常只返回一个 `srcUrl` MP4，元数据里可能没有宽高和时长。
3. 下载后使用 PyAV 补充实际宽高、时长、音频和文件大小。
4. 只有一个格式时，分辨率范围以实际文件探测值为准。

## 命令

```bash
python3 scripts/downloader/pearvideo_downloader.py --check --json
```

```bash
python3 scripts/downloader/pearvideo_downloader.py \
  "<pearvideo_url>" \
  --quality lowest \
  --print-url \
  --json
```

```bash
python3 scripts/downloader/pearvideo_downloader.py \
  "<pearvideo_url>" \
  --quality lowest \
  --attempts 3 \
  --output-dir downloads \
  --json
```

## 已观察结果

- 公开样本匿名完整下载成功。
- extractor 只暴露一个 `srcUrl` MP4，没有预先提供分辨率。
- 下载后实际探测为 406×720 竖屏、含音频，时长约 24.8 秒。

## 故障处理

- `Unable to extract title`：页面或内容 ID 可能已失效。
- `srcUrl` 缺失：页面不再公开媒体地址或 extractor 已失配。
- 只有 App 页面：当前不支持，不要要求用户提供登录 Cookie。
- CDN URL 过期：重新解析后立即下载，不要长期缓存。
