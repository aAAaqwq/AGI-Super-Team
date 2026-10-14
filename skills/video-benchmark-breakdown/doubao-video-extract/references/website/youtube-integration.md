# YouTube 下载集成记录

YouTube 公共 watch 视频下载器已进入 `video-extract`，并接入统一入口。

实现依据 2026-07-30 的真实样例实验：

- 报告：<https://tosv.byted.org/obj/dmc-supagent/auto-trace-reports/report_20260730002206D3C072D626DD6C61933F.html>
- 样例：`https://www.youtube.com/watch?v=yhn501096Fc`
- 原结果：Android player client 的 format `18` 成功下载约 27 MB 的 360p MP4

## 文件

- `references/website/youtube.md`：平台 reference。
- `scripts/downloader/youtube_downloader.py`：正式下载器。
- `../tests/test_youtube_downloader.py`：不触网单元测试。

## 集成边界

- 统一入口只识别 `youtube.com/watch?v=<11-character-video-id>`。
- 默认 Android player client，优先 format `18`。
- format `18` 缺失时，只从实际格式中选择音视频合一 MP4。
- 不读取 Cookie，不使用 PO Token，不下载平台字幕。
- 在线视频进入飞书妙记链路时，继续遵守“先转音频、禁止上传下载得到的视频文件”的约束。

## 本次自测

2026-07-30 使用 `yt-dlp 2026.07.04` 对原样例完成验证：

- 联网解析成功，选择 format `18`
- MP4，640×360，H.264 + AAC
- 下载文件大小：27,910,649 字节
- PyAV 检查：1 路视频、1 路音频
- 实测时长：857.768 秒
- 测试文件位于系统临时目录，验证完成后已删除

## 后续扩展

至少补充以下真实回归样本后，再考虑扩大输入范围：

- 普通公开视频；
- 只有音视频分离格式的视频；
- `youtu.be` 短链和分享文本；
- Shorts；
- 播放列表中的单条视频；
- 年龄、地区、登录、私密或删除限制；
- format `18` 缺失、SABR、PO Token、403、429。

不要只根据单条成功样本扩大支持范围，也不要把 format `18` 当成所有视频都存在的固定格式。
