#!/usr/bin/env python3
"""Match model-provided terms against transcript segments and return time windows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "video_extract"))

from transcript_parser import ms_to_timestamp, parse_transcript_file  # noqa: E402


def _load_terms(terms_json: str, extra_terms: list[str]) -> list[str]:
    terms: list[str] = []
    if terms_json:
        parsed = json.loads(terms_json)
        if not isinstance(parsed, list):
            raise ValueError("--terms must be a JSON array of strings")
        terms.extend(str(term).strip() for term in parsed if str(term).strip())
    terms.extend(term.strip() for term in extra_terms if term.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        key = term.casefold()
        if key not in seen:
            seen.add(key)
            deduped.append(term)
    if not deduped:
        raise ValueError("Provide at least one matched term via --terms or --term")
    return deduped


def _segment_end(segment: dict[str, Any], default_ms: int = 5000) -> int:
    end_ms = segment.get("end_ms")
    if isinstance(end_ms, int):
        return end_ms
    return int(segment["start_ms"]) + default_ms


def match_transcript_windows(
    transcript_path: str | Path,
    terms: list[str],
    pre_roll_seconds: float = 5,
    post_roll_seconds: float = 8,
    merge_gap_seconds: float = 10,
    max_windows: int = 8,
) -> dict[str, Any]:
    segments = parse_transcript_file(transcript_path)
    term_keys = [(term, term.casefold()) for term in terms]
    matches: list[dict[str, Any]] = []

    for segment in segments:
        text = str(segment.get("text", ""))
        folded = text.casefold()
        matched_terms = [term for term, key in term_keys if key in folded]
        if not matched_terms:
            continue
        start_ms = max(0, int(segment["start_ms"]) - int(pre_roll_seconds * 1000))
        end_ms = _segment_end(segment) + int(post_roll_seconds * 1000)
        matches.append(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "matched_terms": matched_terms,
                "segments": [segment],
            }
        )

    merge_gap_ms = int(merge_gap_seconds * 1000)
    windows: list[dict[str, Any]] = []
    for match in matches:
        if windows and match["start_ms"] <= windows[-1]["end_ms"] + merge_gap_ms:
            window = windows[-1]
            window["end_ms"] = max(window["end_ms"], match["end_ms"])
            window["matched_terms"] = sorted(set(window["matched_terms"]) | set(match["matched_terms"]))
            window["segments"].extend(match["segments"])
        else:
            windows.append(match)

    windows = windows[:max_windows]
    for index, window in enumerate(windows, start=1):
        window["window_id"] = f"window-{index:03d}"
        window["start_time"] = ms_to_timestamp(window["start_ms"])
        window["end_time"] = ms_to_timestamp(window["end_ms"])
        window["transcript_excerpt"] = "\n".join(
            f'{segment["speaker"]} {segment["start_time"]}\n{segment["text"]}'
            for segment in window["segments"]
        )

    return {
        "transcript": str(Path(transcript_path).expanduser().resolve()),
        "terms": terms,
        "windows": windows,
        "count": len(windows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Match model-provided terms against a transcript and return time windows."
    )
    parser.add_argument("transcript", help="Path to transcript.txt")
    parser.add_argument("--terms", default="", help='JSON array, for example: ["金字塔"]')
    parser.add_argument("--term", action="append", default=[], help="Add one matched term.")
    parser.add_argument("--pre-roll", type=float, default=5, help="Seconds before each match.")
    parser.add_argument("--post-roll", type=float, default=8, help="Seconds after each match.")
    parser.add_argument("--merge-gap", type=float, default=10, help="Merge windows within this many seconds.")
    parser.add_argument("--max-windows", type=int, default=8, help="Maximum windows to return.")
    parser.add_argument("--output", help="Write matched windows JSON to this path.")
    args = parser.parse_args()

    try:
        terms = _load_terms(args.terms, args.term)
        payload = match_transcript_windows(
            args.transcript,
            terms,
            pre_roll_seconds=args.pre_roll,
            post_roll_seconds=args.post_roll,
            merge_gap_seconds=args.merge_gap,
            max_windows=args.max_windows,
        )
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"Transcript window match failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
