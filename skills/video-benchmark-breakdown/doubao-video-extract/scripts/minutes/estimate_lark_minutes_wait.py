#!/usr/bin/env python3
"""Estimate Lark Minutes processing and timeout windows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Optional


def _format_seconds(seconds: int) -> str:
    minutes, remaining_seconds = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{remaining_seconds:02d}s"
    if minutes:
        return f"{minutes}m{remaining_seconds:02d}s"
    return f"{remaining_seconds}s"


def probe_media_duration_seconds(media_path: str | Path) -> float:
    try:
        import av  # type: ignore
    except Exception as exc:
        raise RuntimeError("PyAV is required to probe media duration. Pass --duration-seconds if PyAV is unavailable.") from exc

    media = Path(media_path).expanduser().resolve()
    if not media.exists():
        raise FileNotFoundError(f"Media file not found: {media}")

    container = av.open(str(media))
    try:
        if container.duration is not None:
            return float(container.duration) / 1_000_000
        stream_durations = []
        for stream in container.streams:
            if stream.duration is not None and stream.time_base is not None:
                stream_durations.append(float(stream.duration * stream.time_base))
        if stream_durations:
            return max(stream_durations)
    finally:
        container.close()

    raise ValueError(f"Unable to determine media duration: {media}")


def estimate_wait_window(
    duration_seconds: float,
    *,
    notes_retries: int = 10,
    notes_wait_seconds: int = 30,
    processing_ratio: float = 0.1,
    timeout_ratio: float = 0.2,
) -> dict[str, Any]:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than 0")
    if notes_retries < 0:
        raise ValueError("notes_retries must be >= 0")
    if notes_wait_seconds < 0:
        raise ValueError("notes_wait_seconds must be >= 0")

    estimated_processing_seconds = int(math.ceil(duration_seconds * processing_ratio))
    timeout_seconds = int(math.ceil(duration_seconds * timeout_ratio))
    helper_poll_seconds = int(notes_retries * notes_wait_seconds)
    return {
        "media_duration_seconds": duration_seconds,
        "media_duration_human": _format_seconds(int(math.ceil(duration_seconds))),
        "estimated_processing_seconds": estimated_processing_seconds,
        "estimated_processing_human": _format_seconds(estimated_processing_seconds),
        "timeout_seconds": timeout_seconds,
        "timeout_human": _format_seconds(timeout_seconds),
        "helper_poll_seconds": helper_poll_seconds,
        "helper_poll_human": _format_seconds(helper_poll_seconds),
        "notes_retries": notes_retries,
        "notes_wait_seconds": notes_wait_seconds,
        "processing_ratio": processing_ratio,
        "timeout_ratio": timeout_ratio,
        "note": (
            "Estimated processing and timeout windows are guidance for deciding whether to wait or report timeout. "
            "helper_poll_seconds is the script's default polling wait cap."
        ),
    }


def estimate_from_media(
    media_path: str | Path,
    *,
    notes_retries: int = 10,
    notes_wait_seconds: int = 30,
) -> dict[str, Any]:
    duration_seconds = probe_media_duration_seconds(media_path)
    payload = estimate_wait_window(
        duration_seconds,
        notes_retries=notes_retries,
        notes_wait_seconds=notes_wait_seconds,
    )
    payload["media_path"] = str(Path(media_path).expanduser().resolve())
    return payload


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate Lark Minutes wait and timeout windows.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--media", help="Local media file to probe with PyAV.")
    source.add_argument("--duration-seconds", type=float, help="Known media duration in seconds.")
    parser.add_argument("--notes-retries", type=int, default=10, help="vc +notes retry count. Defaults to 10.")
    parser.add_argument("--notes-wait", type=int, default=30, help="Seconds between vc +notes retries. Defaults to 30.")
    args = parser.parse_args(argv)

    try:
        if args.media:
            payload = estimate_from_media(
                args.media,
                notes_retries=args.notes_retries,
                notes_wait_seconds=args.notes_wait,
            )
        else:
            payload = estimate_wait_window(
                args.duration_seconds,
                notes_retries=args.notes_retries,
                notes_wait_seconds=args.notes_wait,
            )
        print(json.dumps({"success": True, "data": payload}, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
