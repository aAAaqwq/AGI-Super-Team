# 微博下载集成记录

微博公共视频的轻量解析、下载和测试已融合进 `video-extract`。

## 文件

- `references/website/weibo.md`：平台说明。
- `scripts/downloader/weibo_downloader.py`：纯 Python 标准库下载器。
- `../tests/test_weibo_downloader.py`：不触网单元测试。

## 本地验证

```bash
python3 scripts/downloader/weibo_downloader.py placeholder --check --json
python3 -m unittest discover -s ../tests -p 'test_weibo_downloader.py' -v
```

真实链接只解析：

```bash
python3 scripts/downloader/weibo_downloader.py \
  "https://weibo.com/tv/show/1034:5323743128387592?mid=5323743317464766" \
  --quality 480p \
  --print-url \
  --json
```

真实链接下载：

```bash
python3 scripts/downloader/weibo_downloader.py \
  "https://weibo.com/tv/show/1034:5323743128387592?mid=5323743317464766" \
  --quality 480p \
  --output-dir downloads \
  --json
```

## 后续回归范围

继续准备至少 5 条真实公开视频回归样本，覆盖：

- 带 `mid` 的 PC 视频页；
- H5 视频页；
- 分享文本；
- 缺少目标清晰度时的降级；
- 临时 CDN URL 过期刷新；
- 删除、私密、非视频输入的结构化失败。

`t.cn` 短链当前不在支持范围内；如需加入，应先实现并测试短链展开到含 OID 的微博视频页，再声明平台分发支持。

不要只根据单条成功样本扩大支持范围。
