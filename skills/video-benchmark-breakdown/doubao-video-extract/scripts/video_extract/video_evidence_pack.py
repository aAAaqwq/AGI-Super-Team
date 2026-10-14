#!/usr/bin/env python3
"""Build a transcript and frame evidence pack for a video understanding query."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "video_extract"))

from transcript_parser import parse_transcript_file  # noqa: E402
from transcript_window_matcher import _load_terms, match_transcript_windows  # noqa: E402
from video_frame_extract import extract_frames  # noqa: E402


def build_evidence_pack(
    video_path: str,
    transcript_path: str,
    terms: list[str],
    output_dir: str = "evidence",
    sample_every_seconds: float = 2,
    max_frames_per_window: int = 8,
) -> dict[str, str]:
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    parsed_payload = {
        "transcript": str(Path(transcript_path).expanduser().resolve()),
        "segments": parse_transcript_file(transcript_path),
    }
    parsed_payload["count"] = len(parsed_payload["segments"])
    transcript_json = out_dir / "transcript_segments.json"
    transcript_json.write_text(json.dumps(parsed_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    windows_payload = match_transcript_windows(transcript_path, terms)
    windows_json = out_dir / "matched_windows.json"
    windows_json.write_text(json.dumps(windows_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    frames_payload = extract_frames(
        video_path,
        windows_payload["windows"],
        out_dir / "frames",
        sample_every_seconds=sample_every_seconds,
        max_frames_per_window=max_frames_per_window,
    )
    frames_json = out_dir / "frames_manifest.json"
    frames_json.write_text(json.dumps(frames_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    context_md = out_dir / "answer_context.md"
    context_lines = [
        "# Video Evidence Context",
        "",
        f"- Video: {Path(video_path).expanduser().resolve()}",
        f"- Transcript: {Path(transcript_path).expanduser().resolve()}",
        f"- Matched terms: {', '.join(terms)}",
        f"- Matched windows: {windows_payload['count']}",
        f"- Extracted frames: {frames_payload['count']}",
        "",
        "Use the transcript excerpts and extracted frame images as evidence. If no windows or no frames are available, say the visual evidence is insufficient.",
    ]
    context_md.write_text("\n".join(context_lines) + "\n", encoding="utf-8")

    return {
        "output_dir": str(out_dir),
        "transcript_segments": str(transcript_json),
        "matched_windows": str(windows_json),
        "frames_manifest": str(frames_json),
        "answer_context": str(context_md),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a video understanding evidence pack.")
    parser.add_argument("--video", required=True, help="Path to local video file.")
    parser.add_argument("--transcript", required=True, help="Path to transcript.txt.")
    parser.add_argument("--terms", default="", help='JSON array of model-extracted terms, for example: ["金字塔"]')
    parser.add_argument("--term", action="append", default=[], help="Add one matched term.")
    parser.add_argument("--output-dir", default="evidence", help="Evidence pack output directory.")
    parser.add_argument("--sample-every", type=float, default=2, help="Seconds between target frames.")
    parser.add_argument("--max-frames-per-window", type=int, default=8)
    args = parser.parse_args()

    try:
        terms = _load_terms(args.terms, args.term)
        payload = build_evidence_pack(
            args.video,
            args.transcript,
            terms,
            output_dir=args.output_dir,
            sample_every_seconds=args.sample_every,
            max_frames_per_window=args.max_frames_per_window,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"Evidence pack build failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
