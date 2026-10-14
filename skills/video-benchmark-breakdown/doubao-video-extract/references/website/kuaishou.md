# 快手视频解析与下载

## 支持输入

- `kuaishou.com/short-video/<photo_id>`
- `v.kuaishou.com` 短链或分享文本
- 已解析的 `kwaicdn.com` / `oskwai.com` / `kwimgs.com` / MP4 URL

## 实现说明

快手下载器使用移动 H5 页面纯 HTTP 解析：短链用移动 UA 跟随跳转，长链先改写为 `https://v.m.chenzhongtech.com/fw/photo/<photo_id>`，再从页面 HTML/JSON 转义内容提取 CDN MP4 候选并按 `hd15 > b > 其他` 选择。

## 解析命令

```bash
python3 scripts/downloader/kuaishou_downloader.py "<kuaishou_url_or_photo_id_or_mp4_url>" --print-url --json
```

## 下载命令

```bash
python3 scripts/downloader/kuaishou_downloader.py "<kuaishou_url_or_photo_id_or_mp4_url>" --output-dir downloads --json
```

## 故障处理

- 短链解析失败时，先用 `--print-url --json` 查看 normalized / page URL 或错误信息。
- 页面无法解析直链时，先确认作品不是私密、删除或图集/图片作品；再查看 `--print-url --json` 返回的结构化 debug，或使用已有本地 MP4 继续后续链路。
