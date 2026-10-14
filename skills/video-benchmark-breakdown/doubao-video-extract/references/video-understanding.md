# 视频理解证据工作流

当用户询问视频中的视觉或多模态内容时使用本参考，例如某个物体、场景、人物、动作、界面、地点或视觉细节是否出现。

## 核心规则

先用脚本时间轴缩小候选范围，再用 PyAV 抽帧获取视觉证据。不要用抽帧或 OCR 生成字幕。除非用户只询问口播内容，否则不要只凭脚本回答视觉问题。

禁止用浏览器搜索、页面内查找、站内搜索、开发者工具搜索、评论/标题/描述检索、网页字幕面板或网页 OCR 结果替代本工作流。浏览器最多用于打开用户给出的链接或辅助获取原始 URL，不能作为视频内容、关键词定位、原文或截图证据的来源。

## 工作流

1. 确保本地 MP4 存在；需要时用 `scripts/downloader/` 下载。
2. 确保脚本存在；需要时通过飞书妙记生成。
3. 自行从用户自然语言问题中提取匹配词。
   - 用户问题：`视频中有出现过金字塔吗`
   - 传给脚本的 terms：`["金字塔"]`
   - 不要把完整用户问题当作脚本查询。
4. 解析脚本：
   ```bash
   python3 scripts/video_extract/transcript_parser.py ./minutes/.../transcript.txt --output ./evidence/transcript_segments.json
   ```
5. 匹配时间窗：
   ```bash
   python3 scripts/video_extract/transcript_window_matcher.py ./minutes/.../transcript.txt --terms '["金字塔"]' --output ./evidence/matched_windows.json
   ```
6. 抽帧：
   ```bash
   python3 scripts/video_extract/video_frame_extract.py --video ./downloads/video.mp4 --windows ./evidence/matched_windows.json --output-dir ./evidence/frames --manifest ./evidence/frames_manifest.json
   ```
7. 回答前检查抽出的帧图像

## 证据包快捷命令

```bash
python3 scripts/video_extract/video_evidence_pack.py \
  --video ./downloads/video.mp4 \
  --transcript ./minutes/.../transcript.txt \
  --terms '["金字塔"]' \
  --output-dir ./evidence/query-001
```

证据包包含：

- `transcript_segments.json`
- `matched_windows.json`
- `frames_manifest.json`
- `answer_context.md`
- `frames/`

## 回答格式

包含以下内容：

- 结论：`有`、`没有` 或 `不确定`。
- 使用的匹配词。
- 检查过的时间段。
- 触发抽帧的脚本摘录。
- 作为视觉证据的帧路径。
- 时间窗或帧证据不足时说明不确定性。

如果没有脚本时间窗匹配模型提取的词，说明“基于脚本引导的视觉搜索没有找到候选时间段”。如果用户需要更高召回率，询问是否扩大匹配词或对整段视频采样。
