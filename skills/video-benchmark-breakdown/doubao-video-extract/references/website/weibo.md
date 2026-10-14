# 微博视频解析与下载


## 支持输入

- `weibo.com/tv/show/1034:<media_id>` 视频页
- `h5.video.weibo.com/show/1034:<media_id>` 移动视频页
- 包含上述链接的微博分享文本
- `1034:<media_id>` OID

## 实现说明

微博下载器使用移动视频页当前调用的匿名 H5 组件接口，不需要登录、浏览器 Cookie、执行 JavaScript 或计算私有签名。它不是官方文档化的下载 API，接口名称和返回结构存在调整风险：

1. 从输入中提取 `1034:<media_id>` OID。
2. 构造移动页 `https://h5.video.weibo.com/show/<oid>`。
3. 向 `https://h5.video.weibo.com/api/component` 发送表单 POST：

   ```json
   {"Component_Play_Playinfo":{"oid":"1034:<media_id>"}}
   ```

4. 从 `Component_Play_Playinfo.urls` 获取 1080P、720P、480P MP4；低清地址来自 `stream_url`。
5. 默认选择 480P。指定清晰度不存在时，优先降级到不高于目标的最高档；没有更低档时选择最低可用档。

PC 页面可能被导向 `passport.weibo.com/visitor/visitor`，不能用桌面页 HTML 是否含直链来判断可行性。应直接使用移动页组件接口。

组件接口返回的是带 `Expires` 和 `ssig` 的临时 CDN URL。解析和下载必须连续执行，不要长期缓存 URL。下载遇到 403 或 410 时，下载器会重新请求组件接口并重试一次。

## 解析命令

```bash
python3 scripts/downloader/weibo_downloader.py \
  "https://weibo.com/tv/show/1034:5323743128387592?mid=5323743317464766" \
  --quality 480p \
  --print-url \
  --json
```

## 下载命令

```bash
python3 scripts/downloader/weibo_downloader.py \
  "https://weibo.com/tv/show/1034:5323743128387592?mid=5323743317464766" \
  --quality 480p \
  --output-dir downloads \
  --json
```

支持的清晰度参数：

- `best`
- `1080p`
- `720p`
- `480p`（默认）
- `360p`

## 输出字段

基础字段：

- `platform`
- `video_url`
- `file_path`（下载模式）
- `oid`
- `media_id`
- `mid`
- `page_url`
- `quality`
- `quality_label`

`metadata` 中保留：

- 标题、正文
- 作者、作者 ID
- 封面
- 时长、发布时间、画面方向
- 播放、转发、评论、点赞统计
- 可用清晰度列表

## 故障处理

- 页面跳到 visitor 网关：不要解析 PC 页面，使用本下载器的移动组件接口。
- 组件接口返回空数据：确认输入是公开微博视频，而不是图文微博、已删除、私密或受限内容。
- 组件接口任务名变化：检查微博当前 `chunk-common.*.js` 中的 `Component_Play_Playinfo`，不要猜新接口。
- CDN 403/410：临时 URL 可能过期；下载器会自动刷新一次，仍失败时重新运行同一命令。
- 指定清晰度不可用：检查 JSON 输出中的 `metadata.available_qualities` 和实际 `quality`。
- 下载文件为空或不是 MP4：保留错误，不要把临时文件改名为 `.mp4` 成品。

## 已验证案例

- 页面：`https://weibo.com/tv/show/1034:5323743128387592?mid=5323743317464766`
- 组件接口：匿名请求成功
- 返回档位：1080P、720P、480P，另有低清 `stream_url`
- 480P 实际文件：852×480、H.264 + AAC、258.763 秒
- CDN Range 验证：`206 Partial Content`、`Content-Type: video/mp4`、存在 MP4 `ftyp` 文件头
