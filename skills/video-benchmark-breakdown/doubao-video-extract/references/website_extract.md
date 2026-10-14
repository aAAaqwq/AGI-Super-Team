# 在线网站视频解析与下载

当用户提供在线视频网站链接、短链、分享文本、本地视频文件或视频直链，且目标是解析视频地址、下载 MP4、保存本地视频，或后续要上传飞书妙记时，先使用本参考。

## 通用流程

- 支持快手、B 站、AcFun、CCTV/CNTV 网页点播、芒果 TV、梨视频、搜狐视频、腾讯视频、微博公开视频、X 公开视频帖子、Facebook Reels、Instagram Reels、TikTok 完整视频页、Twitch Clips、YouTube `youtube.com/watch` 公共视频、视频直链和本地视频。YouTube 的 `youtu.be`、Shorts、播放列表、直播以及登录、会员、年龄或地区受限内容不在当前范围。其他网站的普通视频页面不要尝试浏览、搜索、下载或排障，直接且只回复 `抱歉，不支持解析该网站的视频`。不要追加解释、建议、命令或具体域名。
- 只下载视频、保存 MP4、拿视频直链、解析分享链接：只执行本参考，不进入飞书妙记链路。
- 提取字幕、逐字稿、文案、脚本、总结、章节或时间轴：不要先单独下载，直接进入 `references/lark-minutes-handoff.md` 并使用 `--run-lark`。
- 画面理解、关键帧、物体/动作出现判断：先按本参考下载本地 MP4；如果还需要脚本或时间轴，再进入飞书妙记链路。
- 本地视频文件无需下载，直接作为后续媒体输入。
- 在线链接进入妙记链路时必须先转换为音频，禁止上传下载得到的视频文件；本地文件才允许直接上传视频。
- 默认使用统一入口；平台 downloader 只用于统一入口失败后的专项排障。

预检输入、平台识别和依赖：

```bash
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --check --json
```

下载视频到本地：

```bash
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video
```

普通下载无需增加清晰度、重试或超时参数。共享匿名下载器会向 stderr 实时输出阶段和进度，stdout 保留最终结构化结果；只有用户明确指定清晰度或专项排障时才覆盖默认参数，具体见平台说明。

注意：不加 `--run-lark` 时不会上传飞书妙记。在线链接使用 `--media-mode video` 仅用于下载，不会生成视频上传命令。

## 运行时与依赖契约

- 统一入口会按实际任务自动预检依赖，不要求 Agent 增加参数：yt-dlp 平台检查 yt-dlp；在线音频转换检查 PyAV；只有 `--run-lark` 才检查 `lark-cli`。
- 预检只检查和报告，不自动安装、升级依赖，也不索取管理员权限。版本策略见 `dependencies.json`；yt-dlp 使用当前受支持版本并报告实际版本，不永久精确锁死。
- 媒体读取、校验、抽帧和音频转换统一使用 PyAV。Skill 不依赖、不探测也不调用 FFmpeg/ffprobe。
- AcFun、CCTV、芒果 TV、梨视频、搜狐、腾讯、Facebook Reels、Instagram Reels、TikTok、Twitch Clips、X 和 YouTube 的 yt-dlp 下载阶段复用 `scripts/downloader/download_runtime.py`，共享实时进度、单次解析复用、超时、重试和输出目录策略。平台模块只保留 URL、extractor、格式或匿名边界差异。
- 所有平台失败输出统一包含 `success=false`、`error`、`error_code`、`error_type`、`stage`、`retryable`、`next_action` 和 `attempts`；数字退出码仅表示 CLI 成败，不承载具体失败原因。
- 输出目录不可写时自动降级到可写缓存目录，并在 stderr 输出 `output_fallback` 状态；最终 JSON 的 `output_directory` 同时给出 `requested`、`actual`、`fallback_used` 和 `fallback_reason`。

## 通用输出规范

解析或下载成功时，保留能拿到的结构化字段。不要因为后续只需要 MP4 就丢弃元数据。

基础字段：

- `platform`
- `video_url` 或 `url`
- `file_path`
- `output_directory`
- 平台 ID，例如 `video_id`、`note_id`、`photo_id`、`bvid`、`aid`、`cid`
- `page_url` / `share_url`

附加字段放入 `metadata`：

- 标题、描述、作者、作者 ID
- 封面 URL
- 时长、宽高、发布时间
- 统计数据
- B 站分页信息

字段以实际平台返回为准；拿不到时返回空对象或省略，不要编造。

## 通用实现约束

- 所有下载器都应支持整段分享文本中的首个 URL。
- 脚本不会安装依赖、浏览器扩展或登录凭证。
- 链接需要登录、私密、删除或平台风控时，不要编造视频地址，向用户说明限制。

## 平台说明

根据输入来源读取对应平台说明：

- 快手：`references/website/kuaishou.md`
- B 站：`references/website/bilibili.md`
- AcFun：`references/website/acfun.md`
- CCTV/CNTV 网页点播：`references/website/cctv.md`
- 芒果 TV：`references/website/mgtv.md`
- 梨视频：`references/website/pearvideo.md`
- 搜狐视频：`references/website/sohu.md`
- 腾讯视频：`references/website/tencent-video.md`
- 微博视频：`references/website/weibo.md`
- X 视频帖子：`references/website/x.md`
- Facebook Reels：`references/website/facebook-reels.md`
- Instagram Reels：`references/website/instagram-reels.md`
- TikTok：`references/website/tiktok.md`
- Twitch Clips：`references/website/twitch-clips.md`
- YouTube watch 视频：`references/website/youtube.md`
- 直链视频：`references/website/direct-video.md`
- 本地视频：`references/website/local-video.md`
