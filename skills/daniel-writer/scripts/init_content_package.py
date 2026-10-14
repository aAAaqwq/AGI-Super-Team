#!/usr/bin/env python3
"""为真实项目创建可审计的多平台内容工作包脚手架。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PLATFORM_HINTS = {
    "x": "真实冲动 / 最多三个事实 / 触发与失效 / 责任型结尾",
    "wechat": "标题 / 开场问题 / 背景与约束 / 分步方法 / 证据化案例 / 总结 / CTA",
    "xiaohongshu": "封面 / 钩子 / 要点 / 配图卡片 / 风险提示 / 收藏型 CTA",
    "douyin": "3 秒钩子 / 口播 / 画面 / 字幕 / 节拍时长 / CTA",
    "bilibili": "学习承诺 / 章节 / 前提 / 完整演示 / 常见错误 / 复盘",
    "zhihu": "可回答问题 / 限定结论 / 证据链 / 反例 / 讨论问题",
}


def parse_platforms(raw: str) -> list[str]:
    platforms = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not platforms:
        raise argparse.ArgumentTypeError("至少提供一个平台")
    if len(platforms) != len(set(platforms)):
        raise argparse.ArgumentTypeError("平台名称不能重复")
    for platform in platforms:
        if not platform.replace("-", "").isalnum():
            raise argparse.ArgumentTypeError(f"非法平台名称: {platform}")
    return platforms


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"文件已存在，拒绝覆盖: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_package(output: Path, project_name: str, platforms: list[str], force: bool) -> None:
    if output.exists() and any(output.iterdir()) and not force:
        raise FileExistsError(f"输出目录非空，拒绝覆盖: {output}")
    output.mkdir(parents=True, exist_ok=True)

    files = {
        "00-brief.md": f"""# 内容简报：{project_name}

- 目标受众：TODO
- 业务/教学目标：TODO
- 核心承诺：TODO（需证据支持）
- 内容平台：{', '.join(platforms)}
- 语气：TODO
- 截止时间：TODO
- 不可公开信息：TODO
""",
        "01-evidence-ledger.md": """# 证据账本

| ID | 可发布主张 | 证据位置 | 等级 | 可公开 | 脱敏/备注 |
|---|---|---|---|---|---|
| E-001 | TODO | TODO | 待确认 | 待确认 | TODO |
""",
        "02-story-map.md": """# 母故事

## 受众问题

TODO

## 约束与选择

TODO [E-___]

## 实施过程

TODO [E-___]

## 结果与可复用方法

TODO [E-___]
""",
        "99-publish-checklist.md": """# 发布前检查

- [ ] 所有数字、结果和引用均可追溯到证据 ID
- [ ] 待确认主张未作为事实发布
- [ ] 凭据、隐私、内部链接和未授权素材已移除
- [ ] 每个平台使用原生结构，而非机械缩写
- [ ] 图片有文字说明；视频有字幕稿
- [ ] 链接、CTA、标题和封面文案已人工复核
- [ ] 已获得所需发布授权
""",
    }

    deliverables = []
    for platform in platforms:
        relative_path = f"deliverables/{platform}.md"
        hint = PLATFORM_HINTS.get(
            platform,
            "受众与场景 / 原生格式约束 / 内容结构 / 素材清单 / CTA / 风险",
        )
        files[relative_path] = f"""# {platform} 交付稿

- 目标受众：TODO
- 单一目标：TODO
- 推荐结构：{hint}

## 成稿

TODO（关键事实引用 `[E-___]`）

## 素材与制作说明

TODO

## 发布信息

- 标题/封面：TODO
- CTA：TODO
- 待确认：TODO
"""
        deliverables.append({"platform": platform, "path": relative_path, "status": "draft"})

    for relative_path, content in files.items():
        write_file(output / relative_path, content, force)

    manifest = {
        "schema_version": "1.0",
        "project_name": project_name,
        "evidence_policy": "unverified claims must not be published as facts",
        "deliverables": deliverables,
    }
    write_file(
        output / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        force,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="工作包输出目录")
    parser.add_argument("--project-name", required=True, help="真实项目名称")
    parser.add_argument(
        "--platforms",
        type=parse_platforms,
        default=parse_platforms("wechat,xiaohongshu,douyin,bilibili"),
        help="逗号分隔的平台名称",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已存在的脚手架文件")
    args = parser.parse_args()

    try:
        build_package(args.output_dir, args.project_name.strip(), args.platforms, args.force)
    except (FileExistsError, OSError) as exc:
        parser.error(str(exc))
    print(f"已创建内容工作包: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
