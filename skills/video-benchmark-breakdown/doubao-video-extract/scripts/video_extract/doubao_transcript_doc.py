#!/usr/bin/env python3
"""Render a Lark Minutes transcript as a Doubao-friendly Markdown document."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "video_extract"))

from transcript_parser import parse_transcript_file  # noqa: E402


def _line(value: Optional[Any], fallback: str = "") -> str:
    if value in (None, "", {}, []):
        return fallback
    return str(value)


def render_doubao_transcript_doc(
    transcript_path: str | Path,
    *,
    title: str = "视频逐字稿",
    source_url: Optional[str] = None,
    media_path: Optional[str] = None,
    minute_url: Optional[str] = None,
) -> str:
    transcript = Path(transcript_path).expanduser().resolve()
    segments = parse_transcript_file(transcript)

    lines = [
        f"# {title}",
        "",
        "## 基本信息",
        "",
        f"- 逐字稿文件：`{transcript}`",
    ]
    if source_url:
        lines.append(f"- 来源链接：{source_url}")
    if media_path:
        lines.append(f"- 媒体文件：`{Path(media_path).expanduser().resolve()}`")
    if minute_url:
        lines.append(f"- 飞书妙记：{minute_url}")

    lines.extend(["", "## 逐字稿", ""])
    if not segments:
        lines.append("未解析到逐字稿片段。")
    for segment in segments:
        speaker = _line(segment.get("speaker"), "未知说话人")
        start_time = _line(segment.get("start_time"), "00:00:00.000")
        text = _line(segment.get("text")).replace("\n", " ")
        lines.append(f"- [{start_time}] {speaker}：{text}")

    lines.append("")
    return "\n".join(lines)


def write_doubao_transcript_doc(
    transcript_path: str | Path,
    output_path: str | Path,
    **kwargs: Any,
) -> str:
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_doubao_transcript_doc(transcript_path, **kwargs), encoding="utf-8")
    return str(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render transcript.txt as a Doubao-friendly Markdown document.")
    parser.add_argument("transcript", help="Path to transcript.txt.")
    parser.add_argument("--output", required=True, help="Output Markdown path.")
    parser.add_argument("--title", default="视频逐字稿", help="Document title.")
    parser.add_argument("--source-url", help="Original video URL.")
    parser.add_argument("--media-path", help="Local media file path.")
    parser.add_argument("--minute-url", help="Lark Minutes URL.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    args = parser.parse_args()

    try:
        output = write_doubao_transcript_doc(
            args.transcript,
            args.output,
            title=args.title,
            source_url=args.source_url,
            media_path=args.media_path,
            minute_url=args.minute_url,
        )
        payload = {"success": True, "data": {"doubao_doc_file": output}}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(output)
    except Exception as exc:
        if args.json:
            print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Doubao transcript document render failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
