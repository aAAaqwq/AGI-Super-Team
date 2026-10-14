# B 站视频解析与下载

## 支持输入

- `bilibili.com`
- `b23.tv` 短链
- B 站分享文本
- BV ID
- AV ID

## 实现说明

B 站下载器使用公开 player API，未登录默认使用 480P 或以下清晰度。

B 站只支持通过统一入口或平台 downloader 解析/下载 MP4 与元数据；不要调用 B 站播放器字幕 API，不要读取平台字幕轨道，不要要求用户登录 B 站或复用浏览器 Cookie。

处理 `b23.tv` 短链时，必须先解析 302 跳转后的完整 URL，并保留 URL query 中的风控/分享参数。不要把短链最终地址截断成纯 `https://www.bilibili.com/video/BV.../`，否则容易丢失 `buvid`、`timestamp`、`share_session_id`、`share_source`、`share_medium`、`share_plat`、`up_id` 等参数并触发 412。

如果用户同时提供短链和纯 BV/AV ID，优先使用短链或短链解析后的完整带参 URL。纯 BV/AV ID 只能作为兜底输入。

## 解析命令

```bash
python3 scripts/downloader/bilibili_downloader.py "<bilibili_share_url_b23_bv_or_av>" --print-url --json
```

## 下载命令

```bash
python3 scripts/downloader/bilibili_downloader.py "<bilibili_share_url_b23_bv_or_av>" --output-dir downloads --json
```

## 故障处理

- 短链解析失败时，先用 `--print-url --json` 查看 normalized / page URL 或错误信息。
- B 站短链遇到 412 时，优先确认 downloader 是否保留了 `b23.tv` 302 后的完整带参 URL；关键参数通常是 `buvid`，仅添加 User-Agent 或 Referer 不一定足够。
- 如果只有纯 BV/AV ID 触发 412，让用户补充原始 `b23.tv` 分享短链或分享文本；不要手工把 URL 简化成标准 BV 页面。
- 高画质失败时，降低到 `--quality 32` 或 `--quality 16`。
- 返回 412/429 时通常是临时风控或请求频率限制，脚本会自动退避重试；仍失败时等待片刻后重跑统一入口或 B 站平台 CLI。
- 下载直链返回 403/412/429 时，脚本会重新获取一次 playurl 后重试下载；不要手工拼 B 站 API、不要手工 curl，也不要添加 Origin、Sec-Fetch-* 等浏览器伪装请求头。
- 文本产物统一来自飞书妙记链路；报告字幕、逐字稿、总结或脚本时说明产物来自妙记，不要声称来自 B 站平台字幕。

## 已知 412 案例沉淀

现象：

- 直接使用 `b23.tv` 短链、纯 BV 号、yt-dlp 或 you-get 访问时返回 `HTTP Error 412: Precondition Failed`。
- 浏览器首次直接打开视频页也可能显示 412，先访问 B 站首页建立基础会话后才正常播放。
- 标准 BV URL 加普通 UA/Referer 仍失败，但使用短链 302 后完整带参 URL 可以成功。

关键结论：

- `b23.tv` 的 302 `Location` 可能包含 `?-Arouter=story&buvid=...&timestamp=...&share_session_id=...&share_source=COPY&share_medium=iphone...`。
- `buvid` 是基础风控中最关键的设备指纹类参数之一，必须保留并透传到后续 playurl 请求。
- 短链解析逻辑应保留完整 query 参数，并将其中的分享/风控参数带入 playurl API；不要只提取 BV ID。

建议预检顺序：

1. 解析短链，获取 302 后完整 URL。
2. 检查完整 URL 是否包含 `buvid` 等分享参数。
3. 用完整 URL 作为 referer，并把分享参数透传到 playurl 请求。
4. 如果仍返回 412/429，等待 10-15 秒后重试。
5. 仍失败时，降低到 `--quality 32` 或 `--quality 16`，或让用户稍后重试/补充原始分享文本。
