#!/usr/bin/env python3
"""Parse Lark Minutes transcript.txt into timestamped JSON segments."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional


SPEAKER_LINE_RE = re.compile(
    r"^(?P<speaker>.+?)\s+(?P<timestamp>\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*$"
)


def timestamp_to_ms(value: str) -> int:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?", value.strip())
    if not match:
        raise ValueError(f"Invalid timestamp: {value}")
    hours, minutes, seconds, millis = match.groups()
    return (
        int(hours) * 3600 * 1000
        + int(minutes) * 60 * 1000
        + int(seconds) * 1000
        + int((millis or "0").ljust(3, "0"))
    )


def ms_to_timestamp(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None
    milliseconds = max(0, int(value))
    hours, remainder = divmod(milliseconds, 3600 * 1000)
    minutes, remainder = divmod(remainder, 60 * 1000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _finish_segment(segments: list[dict[str, Any]], current: Optional[dict[str, Any]]) -> None:
    if current is None:
        return
    current["text"] = "\n".join(current.pop("_lines")).strip()
    if current["text"]:
        segments.append(current)


def parse_transcript_text(text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = SPEAKER_LINE_RE.match(line)
        if match:
            _finish_segment(segments, current)
            timestamp = match.group("timestamp")
            current = {
                "speaker": match.group("speaker").strip(),
                "start_ms": timestamp_to_ms(timestamp),
                "start_time": ms_to_timestamp(timestamp_to_ms(timestamp)),
                "end_ms": None,
                "end_time": None,
                "_lines": [],
            }
            continue

        if current is not None:
            if line.strip():
                current["_lines"].append(line.strip())

    _finish_segment(segments, current)

    for index, segment in enumerate(segments[:-1]):
        next_start = segments[index + 1]["start_ms"]
        segment["end_ms"] = next_start
        segment["end_time"] = ms_to_timestamp(next_start)

    return segments


def parse_transcript_file(path: str | Path) -> list[dict[str, Any]]:
    transcript_path = Path(path).expanduser().resolve()
    return parse_transcript_text(transcript_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a Lark Minutes transcript into JSON.")
    parser.add_argument("transcript", help="Path to transcript.txt")
    parser.add_argument("--output", help="Write parsed segments JSON to this path.")
    args = parser.parse_args()

    try:
        segments = parse_transcript_file(args.transcript)
        payload = {
            "transcript": str(Path(args.transcript).expanduser().resolve()),
            "segments": segments,
            "count": len(segments),
        }
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"Transcript parse failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
