# 短视频制作合同

## 输入门

- 获批脚本版本与 SHA、`approval_scope: content-adaptation-only`。
- 逐项素材路径、SHA、owner、rights、privacy、allowed_use。
- 目标画幅/时长、声音/人物来源、字幕语言和输出父目录。
- 输出父目录存在、目标目录不存在，且不经过符号链接。

## 固定交付

- `timeline`：镜头、音频、字幕、转场、证据 ID。
- `preview`：本地候选，不含发布授权。
- `subtitles`：可读、与口播同步、落在安全区。
- `asset-rights-ledger`、`manifest`、`technical-receipt`。
- `human-full-watch`：画面、声音、字幕、事实、隐私、版权、AIGC，默认 pending。

```yaml
status: video-ready-awaiting-human-full-watch
human_full_watch_complete: false
daniel_voice_or_likeness_approved: false
platform_rules_verified: false
external_actions: none
publishing_authorization: none
```

技术检查可记录分辨率、帧率、时长、编码、响度、True Peak、文件大小与 SHA，但不能据此宣称内容质量、真人批准或平台表现。
