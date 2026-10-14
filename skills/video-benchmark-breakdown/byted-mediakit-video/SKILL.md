---
name: byted-mediakit-video
version: 0.2.1
license: MIT
description: "面向视频文件的智能处理、媒资理解、画质治理与画质检测、抽帧、隐私保护、字幕与水印处理、精彩片段与高光拆条分析生成、剧情结构化与剧本整理、场景与语义分段、画面文字识别、视频转码转封装及抠像换脸等目标。若对象和目标族已明确属于视频增强、视频分析理解、视频内容结构化、视频字幕识别或擦除、视频隐私脱敏、视频媒资探测或分发适配，但具体能力不确定，可先加载本 Skill 探索。"
permissions:
- shell
metadata:
  requires:
    bins:
    - mediakit-cli
  cliHelp: mediakit-cli video --help
  product: mediakit-cli-doubao/skills
  domain: video
  capability_count: 30
---
# video MediaKit Skill

## 使用规则

1. 先读取 `../byted-mediakit-shared/SKILL.md`，执行统一前置检查；该 Skill 缺失时停止并报告当前 Skill 包不完整。
2. 只从下表选择 `video` 域工具；相似能力按各工具“能力描述”和参数边界区分。
3. 执行前按需读取对应 reference；参数与结果说明来自同一份已审核文案，完整机器合同以当前 CLI `--schema` 为准。
4. 缺少必填参数、鉴权环境变量或真实输入资源时，向用户索取；通用可选字段只能透传用户明确提供的值，其他可选字段可由明确意图准确确定，但不得伪造。

## 澄清与跨域路由

若只说有视频而未说明业务目标，应先澄清。明确要裁剪、拼接、叠加图片或字幕、混音、合流、调速、转场、画面旋转翻转、视频滤镜或多视频拼画面的成片编辑诉求应路由到 editing；单张图片处理应路由到 image；音频转码、人声分离或语音端点检测应路由到 audio。

## 工具列表

| 工具 | 说明 | 支持模式 | 命令 | 参考 |
| --- | --- | --- | --- | --- |
| add-video-invisible-watermark | 用于视频暗水印添加。在不影响视频画面视觉质量与完整性的前提下，将一串数字信息隐藏式地嵌入视频文件中。适用于视频版权保护、内容泄露溯源、文件真实性校验等场景。 | Cloud | `mediakit-cli video add-video-invisible-watermark` | [reference/add-video-invisible-watermark.md](reference/add-video-invisible-watermark.md) |
| analyze-video-highlights | 支持短剧 Miniseries 和小游戏 Game 两种分析模型，用于高光片段提取，并输出精准时间戳、高光打分、OCR 文本和画面描述，供二次开发或内容分析。 | Cloud | `mediakit-cli video analyze-video-highlights` | [reference/analyze-video-highlights.md](reference/analyze-video-highlights.md) |
| analyze-video-storyline | 用于剧情故事线分析，基于大模型视频理解分析单个或多个长视频并生成结构化剧情数据。分析结果包含两部分：按时间顺序排列的剧情片段，以及基于视频片段整理和归纳出的高光故事线。 | Cloud | `mediakit-cli video analyze-video-storyline` | [reference/analyze-video-storyline.md](reference/analyze-video-storyline.md) |
| asr-subtitles | 从视频或音频的语音中识别并提取带时间戳的字幕文本；适用于提取视频字幕、语音转字幕、听写对白等诉求。识别对象是音轨中的语音内容，不是画面上已烧录的硬字幕。 | Cloud | `mediakit-cli video asr-subtitles` | [reference/asr-subtitles.md](reference/asr-subtitles.md) |
| assess-video-quality | 用于视频画质检测。 | Cloud | `mediakit-cli video assess-video-quality` | [reference/assess-video-quality.md](reference/assess-video-quality.md) |
| drama-recap | 基于已完成的剧本还原任务，可使用自定义解说词或由 AI 自动生成解说词，生成带 AI 配音与解说字幕的营销或解说视频；可配置音色、字幕样式与原文字幕擦除。 | Cloud | `mediakit-cli video drama-recap` | [reference/drama-recap.md](reference/drama-recap.md) |
| drama-recap-vertical | 基于输入短剧剧集的角色与剧情故事线理解，自动提取高光片段并生成全新解说视频；支持文字解说（原片高光混剪 + 屏幕文字）与旁白解说（原片高光混剪 + AI 语音 + BGM），并可套用短剧三要素视觉模板。 | Cloud | `mediakit-cli video drama-recap-vertical` | [reference/drama-recap-vertical.md](reference/drama-recap-vertical.md) |
| drama-script | 基于大模型视频理解能力，将短剧视频转化为结构化剧本文本，识别并提取场景、人物、对话和情节等核心元素。 | Cloud | `mediakit-cli video drama-script` | [reference/drama-script.md](reference/drama-script.md) |
| enhance-video | 用于视频画质增强。利用 AI 算法对输入视频进行分析，并智能执行包括但不限于视频去噪、色彩增强、清晰度提升、瑕疵修复和超分辨率的一系列优化操作。提供 standard 和 professional 两种版本：standard 兼顾处理速度与视频画质，内置高频使用的 10 余种增强算法，适用于视频分发场景的画质增强；professional 提供极致画质增强，内置 30 余种深度 AI 增强算法，适用于影视级视频制作。不同版本会影响增强算法的强度、适用场景与计费。 | Cloud | `mediakit-cli video enhance-video` | [reference/enhance-video.md](reference/enhance-video.md) |
| enhance-video-fast | 集成轻量级超分与智能画质增强，采用速度优先策略，高效兼顾处理效率与画面效果，尤其适用于处理时延敏感的业务场景。 | Cloud | `mediakit-cli video enhance-video-fast` | [reference/enhance-video-fast.md](reference/enhance-video-fast.md) |
| enhance-video-generative | 基于 Diffusion 扩散大模型技术提供生成式视频增强与修复，通过深度语义理解，智能补全和生成符合视频内容的真实细节，可修复视频在压缩或老化过程中损失的像素，最终产出自然、高保真的视频画面。 | Cloud | `mediakit-cli video enhance-video-generative` | [reference/enhance-video-generative.md](reference/enhance-video-generative.md) |
| erase-video-subtitle | 智能检测并擦除视频画面中已有的硬字幕，保留原始背景。<br>支持格式：主流视频格式如mp4、flv、ts、avi、mov、wmv、mkv。 | Cloud | `mediakit-cli video erase-video-subtitle` | [reference/erase-video-subtitle.md](reference/erase-video-subtitle.md) |
| erase-video-subtitle-pro | 用于字幕擦除（精细化版），对视频字幕进行高质量无痕擦除，并最大程度还原视频画面。 | Cloud | `mediakit-cli video erase-video-subtitle-pro` | [reference/erase-video-subtitle-pro.md](reference/erase-video-subtitle-pro.md) |
| extract-frames | 从视频中抽取截图，截图结果支持用于视频封面、预览图、雪碧图或其他视频理解任务的输入。 | Cloud | `mediakit-cli video extract-frames` | [reference/extract-frames.md](reference/extract-frames.md) |
| extract-video-invisible-watermark | 从已嵌入暗水印的视频中解析并还原隐藏的数字信息；如果同一视频被多次嵌入暗水印，也能够提取出所有水印信息。 | Cloud | `mediakit-cli video extract-video-invisible-watermark` | [reference/extract-video-invisible-watermark.md](reference/extract-video-invisible-watermark.md) |
| face-blur-video | 视频人脸打码可自动精准识别视频画面中的人脸区域，并对所有人脸进行模糊或马赛克处理，适用于需要保护人物五官隐私的场景。 | Cloud | `mediakit-cli video face-blur-video` | [reference/face-blur-video.md](reference/face-blur-video.md) |
| face-swap-video | 将用户提供的目标人脸融合替换到视频中的人物上，输出高质量换脸视频，主要适用于生成式视频脱敏需要换脸的场景。 | Cloud | `mediakit-cli video face-swap-video` | [reference/face-swap-video.md](reference/face-swap-video.md) |
| generate-highlights-microdrama | 可用于短剧高光智剪，基于输入剧集的角色和剧情故事线理解提取高光片段，并按时长、产出个数、顺剪或跳剪等要求生成高光混剪、单集预告等视频。 | Cloud | `mediakit-cli video generate-highlights-microdrama` | [reference/generate-highlights-microdrama.md](reference/generate-highlights-microdrama.md) |
| generate-highlights-minigame | 支持识别小游戏录屏视频中的核心玩法与高光事件，例如连击、通关、极限操作，并快速生成用于买量推广的视频素材。可选提供游戏名称、玩法描述和高光定义，辅助更精准地识别精彩内容。 | Cloud | `mediakit-cli video generate-highlights-minigame` | [reference/generate-highlights-minigame.md](reference/generate-highlights-minigame.md) |
| generate-highlights-movie | 支持面向电影、电视剧等长视频内容，按剧情故事线识别高光并拆分成多段指定时长的高光片段，用于影视合集分发的短视频素材；算法会识别并去除景色铺垫、缓慢运镜、片头片尾曲等低密度信息；每段拆条带有高光前置开场与结尾钩子设计。 | Cloud | `mediakit-cli video generate-highlights-movie` | [reference/generate-highlights-movie.md](reference/generate-highlights-movie.md) |
| martencode-video | 极智超清在转码时智能分析视频的场景、动作、内容和纹理，选择最优编码参数，以相对较低码率输出主观画质更优的视频，降低带宽成本并改善用户视觉体验。 | Cloud | `mediakit-cli video martencode-video` | [reference/martencode-video.md](reference/martencode-video.md) |
| matte-greenscreen-video | 可对绿幕或纯色背景的视频进行抠图，自动识别并保留主体，最终生成背景透明或纯色背景的视频。 | Cloud | `mediakit-cli video matte-greenscreen-video` | [reference/matte-greenscreen-video.md](reference/matte-greenscreen-video.md) |
| matte-portrait-video | 自动识别视频中的人物主体，移除原始背景，并生成背景透明或纯色背景的视频文件，适用于背景替换等后期处理场景。 | Cloud | `mediakit-cli video matte-portrait-video` | [reference/matte-portrait-video.md](reference/matte-portrait-video.md) |
| probe-video-metadata | 探测输入的视频 URL，输出标准化的媒资元信息。 | Cloud | `mediakit-cli video probe-video-metadata` | [reference/probe-video-metadata.md](reference/probe-video-metadata.md) |
| remux-video | 视频转封装用于调整视频容器格式，仅修改容器格式，不会重新编解码音视频码流，适用于点播分发适配、流媒体切片打包与多端兼容等场景。 | Cloud | `mediakit-cli video remux-video` | [reference/remux-video.md](reference/remux-video.md) |
| segment-scenes | 依据视频的转场和画面内容变化自动切分多个场景片段，输出每个场景片段的时间轴信息与对应的独立视频文件。 | Cloud | `mediakit-cli video segment-scenes` | [reference/segment-scenes.md](reference/segment-scenes.md) |
| semantic-segment | 综合分析视频的画面、语音和叙事结构，通过镜头切换、语音停顿检测等策略，在保证语义完整、避免将单句从中间切断的前提下，将长视频智能地切分为多个独立的素材片段。 | Cloud | `mediakit-cli video semantic-segment` | [reference/semantic-segment.md](reference/semantic-segment.md) |
| transcode-video | 视频转码将视频码流转换为另一视频码流，可涉及编码格式、分辨率、码率、I 帧间隔和封装格式转换，用于适应不同业务场景、播放终端和网络环境。 | Cloud | `mediakit-cli video transcode-video` | [reference/transcode-video.md](reference/transcode-video.md) |
| video-ocr | 用于视频字幕识别（OCR），识别输入视频画面中的字幕信息，输出带时间戳的结构化文本数据。 | Cloud | `mediakit-cli video video-ocr` | [reference/video-ocr.md](reference/video-ocr.md) |
| video-understand-router | 基于视觉大模型，对输入的视频 URL 列表进行通用视频内容分析，输出视频级别的结构化理解结果，适用于内容审核、视频检索、标签生成等场景。 | Cloud | `mediakit-cli video video-understand-router` | [reference/video-understand-router.md](reference/video-understand-router.md) |
