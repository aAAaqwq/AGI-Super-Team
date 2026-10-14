# 腾讯视频解析与下载


## 支持输入

- `https://v.qq.com/x/page/<video_id>.html`
- `https://v.qq.com/x/cover/<cover_id>/<video_id>.html`
- 包含上述 URL 的分享文本

仅面向无需登录即可播放的公开视频。会员、付费、地区限制、私密、下架及 DRM 内容不在候选范围内。

## 依赖和匿名边界

- Python 3.9+
- `yt-dlp`，脚本只检查，不自动安装或升级
- PyAV 可选；存在时校验视频流、首帧、音频和完整时长

脚本始终使用 `--ignore-config`，不读取浏览器 Cookie，不接收账号、Token 或认证参数。默认最多尝试 3 次，首次完整成功后停止。普通下载无需增加参数；解析、单次下载、网络 socket 和整个重试链路都有默认超时预算。

## 实现说明

腾讯视频使用通用 yt-dlp 下载运行时；下列进度、单次解析复用、重试、错误协议和目录降级能力同时适用于其他 yt-dlp 平台，不在各平台重复实现。

1. 强制要求 yt-dlp 使用 `VQQVideo` extractor，拒绝 Generic extractor。
2. 解析全部媒体格式；展示清晰度时去重，下载失败重试时轮换同清晰度的不同 CDN。
3. 默认选择最低分辨率；可用 `--quality` 指定档位。
4. 单次尝试只解析页面一次，下载阶段复用本次 metadata；临时 metadata 文件在尝试结束后删除。
5. 下载期间向 stderr 实时输出 `resolving`、`downloading`、进度、`verifying` 和 `completed`，stdout 保留最终结果。
6. 登录、会员、DRM、下架等终止错误不会盲目重试；网络、限流、CDN 和媒体不完整错误可在总预算内重试。
7. 下载完成后检查文件存在且非空；有 PyAV 时还要求实际时长不低于页面时长的 90%。
8. JSON 中保留标题、作者、封面、时长、格式 ID、临时媒体 URL、可用分辨率、CDN 选择和实际文件探测结果。
9. 最终结果通过 `output_directory` 明确报告请求目录、实际目录和是否发生降级。

## 命令

环境检查：

```bash
python3 scripts/downloader/tencent_video_downloader.py --check --json
```

只解析最低清晰度：

```bash
python3 scripts/downloader/tencent_video_downloader.py \
  "<tencent_video_url>" \
  --quality lowest \
  --print-url \
  --json
```

匿名下载：

```bash
python3 scripts/downloader/tencent_video_downloader.py \
  "<tencent_video_url>" \
  --quality lowest \
  --attempts 3 \
  --output-dir downloads \
  --json
```

默认参数已包含 `--quality lowest`、`--attempts 3` 和 1800 秒整体预算，Agent 不需要主动传入。只有用户指定清晰度或专项排障时才覆盖：

```bash
python3 scripts/minutes/social_video_to_minutes.py \
  "<tencent_video_url>" \
  --media-mode video \
  --quality 1080p \
  --overall-timeout 900
```

可选排障参数：

- `--socket-timeout`：单次网络读写等待，默认 20 秒。
- `--resolve-timeout`：单次页面解析，默认 90 秒。
- `--download-timeout`：单次下载尝试，默认 1800 秒。
- `--overall-timeout`：包含解析、下载、退避和重试的总预算，默认 1800 秒。

## 已观察结果

- 公开视频样本匿名完整下载成功。
- 样本只暴露 1280×720；8 个格式实际上是同一清晰度的不同 CDN。
- 实际文件为 1280×720、含音频，时长约 216 秒。

这只是单样本范围，不代表腾讯视频所有页面最低都是 720P。

## 故障处理

- extractor 返回“视频不可用”：可能已下架、ID 失效或存在权限限制。
- 只返回会员或 DRM 格式：停止并报告不支持，不要请求 Cookie。
- 多个格式分辨率相同：按 CDN 重复处理，不要把数量误报为清晰度数量。
- 临时媒体 URL 过期：重新运行脚本解析，不要长期缓存 `video_url`。
- stderr 持续出现进度表示任务仍在下载；只有超过 `--overall-timeout` 才按整体超时失败。
