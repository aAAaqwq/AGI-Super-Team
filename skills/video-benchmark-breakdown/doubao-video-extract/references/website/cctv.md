# 央视网页点播解析与下载


## 支持输入

- `https://tv.cctv.com/...` 央视节目网页
- `https://sports.cntv.cn/...` 央视体育节目网页
- 其他由 yt-dlp `CCTV` extractor 明确识别的 `cntv.cn` 公开点播页面
- 包含上述 URL 的分享文本

本实现只代表央视网页点播，不代表央视影音客户端、央视频 `yangshipin.cn`、直播频道、会员或地区限制内容。

## 依赖和匿名边界

- Python 3.10+
- `yt-dlp`
- PyAV 可选，用于媒体完整性验证

脚本忽略 yt-dlp 本机配置，不读取 Cookie、账号或 Token。默认最低分辨率、最多 3 次机会、成功即停止。

## 实现说明

1. 强制要求 `CCTV` extractor，拒绝 Generic extractor。
2. 枚举公开 HLS 格式并默认选择最低分辨率。
3. 下载完成后探测实际宽高、音频和时长。
4. 输入域名虽允许 `cntv.cn` 子域，但最终必须由 `CCTV` extractor 接管。

## 命令

```bash
python3 scripts/downloader/cctv_downloader.py --check --json
```

```bash
python3 scripts/downloader/cctv_downloader.py \
  "<cctv_web_video_url>" \
  --quality lowest \
  --print-url \
  --json
```

```bash
python3 scripts/downloader/cctv_downloader.py \
  "<cctv_web_video_url>" \
  --quality lowest \
  --attempts 3 \
  --output-dir downloads \
  --json
```

## 已观察结果

- `tv.cctv.com` 公开节目样本匿名完整下载成功。
- 样本只暴露 480×270 HLS。
- 实际文件为 480×270、含音频，时长约 38 秒。
- `yangshipin.cn` 不由该 extractor 支持，不能混入本实现。

## 故障处理

- 域名可访问但 extractor 不是 `CCTV`：拒绝 Generic 结果。
- 老 `cntv.cn` 页面 DNS 或页面失效：使用仍在线的节目页，不要猜 API。
- 央视频、客户端或直播 URL：当前不支持。
- HLS 临时地址过期：重新运行解析和下载。

