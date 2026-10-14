#!/usr/bin/env python3
"""Extract representative video frames for transcript-matched time windows using PyAV."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "video_extract"))

from transcript_parser import ms_to_timestamp  # noqa: E402


def _load_windows(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    windows = data.get("windows", data) if isinstance(data, dict) else data
    if not isinstance(windows, list):
        raise ValueError("Windows JSON must contain a list or a top-level `windows` list")
    return windows


def _target_times(start_ms: int, end_ms: int, sample_every_seconds: float, max_frames: int) -> list[int]:
    step_ms = max(1, int(sample_every_seconds * 1000))
    targets = list(range(start_ms, max(start_ms + 1, end_ms + 1), step_ms))
    if not targets:
        targets = [start_ms]
    if len(targets) > max_frames:
        if max_frames == 1:
            return [targets[len(targets) // 2]]
        stride = (len(targets) - 1) / (max_frames - 1)
        return [targets[round(index * stride)] for index in range(max_frames)]
    return targets


def _frame_time_ms(frame: Any) -> int | None:
    if frame.pts is None or frame.time_base is None:
        return None
    return int(float(frame.pts * frame.time_base) * 1000)


def _extract_frame_at(container: Any, stream: Any, target_ms: int) -> tuple[Any, int]:
    container.seek(max(0, target_ms - 1000) * 1000, any_frame=False, backward=True)
    fallback = None
    fallback_ms = target_ms
    for packet in container.demux(stream):
        for frame in packet.decode():
            frame_ms = _frame_time_ms(frame)
            if frame_ms is None:
                continue
            fallback = frame
            fallback_ms = frame_ms
            if frame_ms >= target_ms:
                return frame, frame_ms
        if fallback is not None and fallback_ms >= target_ms:
            break
    if fallback is None:
        raise ValueError(f"No frame decoded near {target_ms} ms")
    return fallback, fallback_ms


def extract_frames(
    video_path: str | Path,
    windows: list[dict[str, Any]],
    output_dir: str | Path,
    sample_every_seconds: float = 2,
    max_frames_per_window: int = 8,
    image_format: str = "jpg",
) -> dict[str, Any]:
    try:
        import av  # type: ignore
    except Exception as exc:
        raise RuntimeError("PyAV is required for frame extraction. Install `av` first.") from exc

    suffix = "jpg" if image_format.lower() in {"jpg", "jpeg"} else "png"
    video = Path(video_path).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, Any]] = []

    container = av.open(str(video))
    try:
        video_streams = [stream for stream in container.streams if stream.type == "video"]
        if not video_streams:
            raise ValueError(f"No video stream found in input video: {video}")
        stream = video_streams[0]

        for window_index, window in enumerate(windows, start=1):
            window_id = window.get("window_id") or f"window-{window_index:03d}"
            window_dir = out_dir / str(window_id)
            window_dir.mkdir(parents=True, exist_ok=True)
            start_ms = int(window["start_ms"])
            end_ms = int(window["end_ms"])
            for target_ms in _target_times(start_ms, end_ms, sample_every_seconds, max_frames_per_window):
                frame, actual_ms = _extract_frame_at(container, stream, target_ms)
                image = frame.to_image()
                frame_path = window_dir / f"{actual_ms:09d}.{suffix}"
                image.save(frame_path, format="JPEG" if suffix == "jpg" else "PNG")
                frames.append(
                    {
                        "path": str(frame_path),
                        "time_ms": actual_ms,
                        "time": ms_to_timestamp(actual_ms),
                        "target_ms": target_ms,
                        "target_time": ms_to_timestamp(target_ms),
                        "window_id": window_id,
                    }
                )
    finally:
        container.close()

    return {
        "video_path": str(video),
        "output_dir": str(out_dir),
        "frames": frames,
        "count": len(frames),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract frames from matched video time windows.")
    parser.add_argument("--video", required=True, help="Path to local video file.")
    parser.add_argument("--windows", required=True, help="Matched windows JSON.")
    parser.add_argument("--output-dir", default="evidence/frames", help="Frame output directory.")
    parser.add_argument("--sample-every", type=float, default=2, help="Seconds between target frames.")
    parser.add_argument("--max-frames-per-window", type=int, default=8)
    parser.add_argument("--format", choices=["jpg", "png"], default="jpg")
    parser.add_argument("--manifest", help="Write frame manifest JSON to this path.")
    args = parser.parse_args()

    try:
        payload = extract_frames(
            args.video,
            _load_windows(args.windows),
            args.output_dir,
            sample_every_seconds=args.sample_every,
            max_frames_per_window=args.max_frames_per_window,
            image_format=args.format,
        )
        if args.manifest:
            manifest_path = Path(args.manifest).expanduser().resolve()
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"Frame extraction failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
