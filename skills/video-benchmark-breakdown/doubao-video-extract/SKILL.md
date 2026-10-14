---
name: doubao-video-extract
description: 可提取、下载、解析、理解在线视频或本地视频文件。支持快手、B 站、AcFun、芒果 TV、梨视频、微博、X 平台、Facebook、Instagram、TikTok、Twitch、YouTube等视频平台、视频直链和本地视频。可提取内容包含视频的音频、字幕、逐字稿、文案、脚本、总结、时间轴。可理解的视频内容包含画面、人物、物体、动作、界面等视觉元素。
---

# 视频提取

## 第零步：外网平台运行环境检查

当输入是 X.com、Facebook、Instagram、TikTok、Twitch、YouTube
或其他需要访问外部网络环境的视频链接时，必须先判断当前环境是网页端还是本地电脑，并确认当前网络能否访问目标平台。

- 本地电脑模式且网络可访问：继续后续解析流程。
- 网页端、云端或无法访问：不要执行下载或解析命令，直接提示用户：

> 当前网络环境无法访问平台内容。请尝试切换到本地电脑模式。如果暂时无法切换，也可以先将视频下载为本地文件并上传，我可以继续进行转写、总结或画面分析。

用户已经提供本地视频文件时，不受上述限制，继续处理。

## 执行目录

执行本 Skill 的任何命令前，先将工作目录切换到包含本 `SKILL.md` 的当前 Skill 根目录：

```bash
cd "<当前 video-extract Skill 文件夹的绝对路径>"
```
例如：
```bash
cd /*/workspace/skills/video-extract/
```

下文的 `scripts/`、`references/`、`downloads/`、`minutes/` 和 `evidence/` 等路径均相对于该 Skill 根目录

## 先选命令

| 用户目标 | 默认动作 | 不要做 |
| --- | --- | --- |
| 只下载、保存 MP4、解析视频地址 | 读 `references/website_extract.md`，运行 `python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video` | 不要进入妙记链路 |
| 要字幕、逐字稿、原文、文案、总结、关键词、时间轴 | 读 `references/lark-minutes-handoff.md` | 不要先单独下载再转写；不要使用未在参考中允许的转写工具 |
| 要截图、画面证据、某物/某人/某动作是否出现 | 先判断是否需要口播/原文定位；需要则先 `--run-lark`，再读 `references/video-understanding.md` 抽帧取证 | 不要全片均匀抽帧大海捞针；不要用浏览器搜索或页面查找替代视频取证 |

## 意图路由

先判断用户要的是 **下载视频**、**转写/提取文本**，还是 **视频画面理解**。

### 视频口令

当用户上传视频口令、暗号、淘口令式文本或平台分享口令，但内容中不包含可访问的视频链接时，不要尝试解析、搜索、猜测或要求联网排障，直接提醒用户：

```text
无法支持对视频口令的解析，请提供视频链接
```
### 支持的网站
支持快手、B 站、AcFun、CCTV、芒果 TV、梨视频、搜狐视频、腾讯视频、微博视频、X.com、Facebook、Instagram、TikTok、Twitch、YouTube、视频直链和本地视频。

### 不支持的网站
YouTube 的 `youtu.be`、Shorts、播放列表、直播以及登录、会员、年龄或地区受限内容不在当前范围。用户要求解析其他网站的普通视频页面时，不要尝试浏览、搜索、下载或排障，直接且只输出：

```text
抱歉，不支持解析该网站的视频
```

不要在这句话前后添加解释、建议或命令，不要提及具体域名。可直接访问的视频文件 URL 不属于“不支持的网站”，继续按视频直链处理。

### 下载视频

当用户只要求下载/保存视频，或只是给出在线视频链接并询问能否解析时：

1. 读取 `references/website_extract.md`。
2. 默认使用统一入口下载/解析：`python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video`。
3. 只有统一入口失败且需要专项排障时，才使用对应平台 downloader 的 `--print-url --json` 或 `--json`。
4. 下载视频的任务无需进入文本提取链路，除非用户明确需要字幕、逐字稿、总结或时间轴。

### 转写与文本提取

当用户要求提取视频的音频、字幕、逐字稿、文案、脚本、总结、章节、关键词或时间轴时：

1. 读取 `references/lark-minutes-handoff.md`。
2. 使用统一入口：`python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --run-lark`。
3. 在线链接必须成功转换为音频后才能上传妙记，禁止上传视频文件；只有用户提供本地文件时才能使用视频上传。
4. 授权预检只在首次使用、排障、用户明确要求，或 `--run-lark` 返回授权错误时执行。
5. 内容提取结果必须来自 `--run-lark` 的转写产物，禁止用浏览器页面或网页元数据代替。

### 视频理解

当用户询问画面、多模态内容、关键帧、某物/某人/某动作是否出现时：

1. 先读取 `references/website_extract.md`，确保有本地 MP4。
2. 如果还需要脚本或时间轴，继续读取 `references/lark-minutes-handoff.md`。
3. 再读取 `references/video-understanding.md`。
4. 禁止用浏览器页面搜索、站内搜索、开发者工具搜索、字幕面板搜索或网页 OCR 结果替代本地 MP4、转写脚本和抽帧证据。

## 脚本布局

- `scripts/downloader/`：各平台解析器，以及所有 yt-dlp 链路复用的下载运行时、进度、重试、错误和输出目录协议。
- `scripts/convert/`：使用 PyAV 进行视频转音频；Skill 不依赖或调用 FFmpeg/ffprobe。
- `scripts/minutes/`：飞书妙记上传、生成与产物读取。
- `scripts/video_extract/`：脚本解析、关键词时间窗匹配、视频抽帧。
- `scripts/util/`：共享工具函数。
- `dependencies.json`：任务依赖和版本策略清单；yt-dlp 记录实际版本但不永久精确锁死。

## 快速命令

```bash
# 默认预检入口，先看 references/website_extract.md 或 references/lark-minutes-handoff.md。
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --check --json

# 只下载或解析在线视频。
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --media-mode video

# 执行飞书妙记链路。
python3 scripts/minutes/social_video_to_minutes.py "<url_or_share_text>" --run-lark
```

## 反模式

- 不要手工 import `scripts.*` 内部函数；使用脚本 CLI。
- 不要手工拼平台直链、curl 平台 API 或从浏览器右键提取视频；失败时先运行统一入口 `--check --json`，再运行平台 downloader 的 `--print-url --json` 排障。
- 不要把“准备本地视频”和“转写文本”拆成两次执行；文本提取任务直接跑 `--run-lark`。
- 不要使用参考文档未明确允许的第三方转写工具。
- 即使 `--run-lark` 返回飞书授权错误，也必须停止并报告授权问题，禁止绕过飞书妙记自行转写。
- 不要全片均匀抽帧找答案；先用逐字稿匹配时间窗，再抽帧取证。
- 不要用浏览器搜索、页面内查找、站内搜索、评论/标题/描述检索或网页字幕面板检索来代替视频分析；浏览器最多用于打开用户给出的链接或辅助获取原始 URL，不能作为“视频内容提取/关键词定位/截图证据”的来源。

## 输出要求

- 报告下载结果时，包含来源平台、保存后的视频文件或解析得到的视频URL。
- 下载结果包含 `output_directory.requested`、`actual`、`fallback_used` 和 `fallback_reason`；发生目录降级时必须向用户展示实际路径。
- 如果解析过程中拿到标题、描述、作者、封面、时长、统计、分页等附加字段，应随下载结果一起返回为结构化字段，不要丢弃。
- 报告文本提取结果时，包含来源平台和提取结果；生成了脚本文件时一并提供，无法取得文本产物时说明限制。
- 用户要求脚本或逐字稿时默认提供豆包文档格式产物，并报告 `doubao_doc_file` 路径。
- 报告飞书妙记结果时，包含来源平台、提取结果、使用到的音频/视频文件、飞书妙记 URL、提取产物文件/路径。
- 报告视频理解结果时，包含检查的结论、时间段、脚本摘录、抽帧图片。
