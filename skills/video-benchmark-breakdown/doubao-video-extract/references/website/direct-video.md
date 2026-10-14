# 直链视频解析与下载

## 支持输入

- 可直接下载的视频 URL。

## 实现说明

直链下载器用 `Content-Type: video/*` 和常见视频扩展名判断。

## 解析命令

```bash
python3 scripts/downloader/direct_video_downloader.py "<direct_video_url>" --check --json
```

## 下载命令

```bash
python3 scripts/downloader/direct_video_downloader.py "<direct_video_url>" --output-dir downloads --json
```

## 故障处理

- 直链被判定为 HTML 时，它不是直接视频地址，需要换平台下载器或浏览器手动解析。
