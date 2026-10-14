#!/usr/bin/env python3
"""Resolve and download public YouTube watch videos with the Android player client."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import download_runtime


PLATFORM = "youtube"
PLAYER_CLIENT = "android"
PREFERRED_FORMAT_ID = "18"
URL_PATTERN = re.compile(r"https?://[^\s，。；;）)】>\]\"']+")
VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}")


class YouTubeDownloadError(download_runtime.DownloadRuntimeError):
    def __init__(
        self,
        message: str,
        detail: str = "",
        *,
        code: Optional[str] = None,
        stage: Optional[str] = None,
        retryable: Optional[bool] = None,
    ):
        inferred_code, inferred_retryable, inferred_stage = (
            download_runtime.classify_error(RuntimeError(f"{message}\n{detail}"))
        )
        self.detail = detail
        super().__init__(
            message,
            code=code or inferred_code,
            stage=stage or inferred_stage,
            retryable=inferred_retryable if retryable is None else retryable,
            detail=detail,
        )


def _success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def _failure(exc: Exception) -> dict[str, Any]:
    return download_runtime.failure_payload(
        exc,
        (
            "Use a public youtube.com/watch?v=<video_id> URL. Login-required, member-only, "
            "age-restricted, region-restricted, private, deleted, live, playlist, Shorts, "
            "and youtu.be inputs are outside the validated scope. Do not add cookies or PO Tokens."
        ),
    )


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _extract_first_url(value: str) -> str:
    match = URL_PATTERN.search(html.unescape(value.strip()))
    if not match:
        raise ValueError("Input does not contain an HTTP(S) YouTube watch URL.")
    return match.group(0)


def normalize_input(value: str) -> str:
    url = _extract_first_url(value)
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("YouTube URL must use HTTP or HTTPS.")
    if host != "youtube.com" and not host.endswith(".youtube.com"):
        raise ValueError("Only youtube.com/watch URLs are supported.")
    if parsed.path.rstrip("/") != "/watch":
        raise ValueError("Only youtube.com/watch URLs are supported.")
    video_id = (parse_qs(parsed.query).get("v") or [""])[0]
    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("YouTube watch URL contains an invalid or missing video ID.")
    return f"https://www.youtube.com/watch?v={video_id}"


def _yt_dlp_runner() -> list[str]:
    return download_runtime.discover_yt_dlp_runner()


def _base_command(
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
) -> list[str]:
    return [
        *_yt_dlp_runner(),
        *download_runtime.common_yt_dlp_options(
            socket_timeout=socket_timeout,
            retries=1,
            fragment_retries=1,
            extractor_retries=1,
        ),
        "--no-warnings",
        "--extractor-args",
        f"youtube:player_client={PLAYER_CLIENT}",
    ]


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    stage = "resolve" if "--dump-single-json" in command else "preflight"
    try:
        return download_runtime.run_capture(
            command,
            timeout=timeout,
            stage=stage,
        )
    except download_runtime.DownloadRuntimeError as exc:
        raise YouTubeDownloadError(
            str(exc),
            detail=exc.detail,
            code=exc.code,
            stage=exc.stage,
            retryable=exc.retryable,
        ) from exc


def _load_metadata(
    page_url: str,
    *,
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
    resolve_timeout: int = 180,
) -> dict[str, Any]:
    download_runtime.emit_status("resolving", platform=PLATFORM, page_url=page_url)
    command = [
        *_base_command(socket_timeout=socket_timeout),
        "--skip-download",
        "--dump-single-json",
        page_url,
    ]
    completed = _run(command, timeout=resolve_timeout)
    try:
        info = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise YouTubeDownloadError(
            "yt-dlp returned invalid JSON metadata.",
            detail=completed.stdout[-1000:].strip(),
        ) from exc
    if not isinstance(info, dict):
        raise YouTubeDownloadError("yt-dlp returned an unexpected metadata value.")
    return info


def _is_muxed_mp4(item: dict[str, Any]) -> bool:
    return (
        item.get("url")
        and str(item.get("ext") or "").lower() == "mp4"
        and item.get("vcodec") not in (None, "", "none")
        and item.get("acodec") not in (None, "", "none")
    )


def _format_score(item: dict[str, Any]) -> tuple[int, int, float, int]:
    return (
        int(item.get("height") or 0),
        int(item.get("width") or 0),
        float(item.get("tbr") or 0),
        int(item.get("filesize") or item.get("filesize_approx") or 0),
    )


def _select_format(
    info: dict[str, Any],
    requested_format_id: Optional[str] = None,
) -> dict[str, Any]:
    formats = [item for item in info.get("formats") or [] if isinstance(item, dict)]
    if requested_format_id:
        selected = next(
            (item for item in formats if str(item.get("format_id")) == requested_format_id),
            None,
        )
        if selected is None:
            raise YouTubeDownloadError(
                f"Requested YouTube format {requested_format_id!r} is unavailable."
            )
        if not _is_muxed_mp4(selected):
            raise YouTubeDownloadError(
                f"Requested YouTube format {requested_format_id!r} is not a muxed MP4."
            )
        return selected

    preferred = next(
        (
            item
            for item in formats
            if str(item.get("format_id")) == PREFERRED_FORMAT_ID and _is_muxed_mp4(item)
        ),
        None,
    )
    if preferred:
        return preferred

    muxed_mp4 = [item for item in formats if _is_muxed_mp4(item)]
    if not muxed_mp4:
        raise YouTubeDownloadError(
            "The Android player client returned no downloadable muxed MP4 format. "
            "Refusing to guess a fixed format or require an external media merger."
        )
    return max(muxed_mp4, key=_format_score)


def _compact_formats(info: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in info.get("formats") or []:
        if not isinstance(item, dict):
            continue
        compact = {
            key: item.get(key)
            for key in (
                "format_id",
                "format_note",
                "ext",
                "width",
                "height",
                "fps",
                "vcodec",
                "acodec",
                "filesize",
                "filesize_approx",
                "tbr",
            )
            if item.get(key) is not None
        }
        if compact:
            result.append(compact)
    return result


def _metadata(info: dict[str, Any]) -> dict[str, Any]:
    statistics = {
        key: info.get(key)
        for key in ("view_count", "like_count", "comment_count")
        if info.get(key) is not None
    }
    metadata = {
        "title": info.get("title"),
        "description": info.get("description"),
        "uploader": info.get("uploader"),
        "uploader_id": info.get("uploader_id"),
        "channel": info.get("channel"),
        "channel_id": info.get("channel_id"),
        "duration": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "timestamp": info.get("timestamp"),
        "thumbnail": info.get("thumbnail"),
        "chapters": info.get("chapters"),
        "statistics": statistics,
        "available_formats": _compact_formats(info),
    }
    return {
        key: value
        for key, value in metadata.items()
        if value not in (None, "", {}, [])
    }


def _public_info(
    info: dict[str, Any],
    page_url: str,
    selected: dict[str, Any],
) -> dict[str, Any]:
    height = selected.get("height")
    return {
        "platform": PLATFORM,
        "video_url": selected["url"],
        "video_id": info.get("id"),
        "page_url": info.get("webpage_url") or page_url,
        "format_id": str(selected.get("format_id")),
        "quality": f"{height}p" if height else selected.get("format_note") or "unknown",
        "selected_format": {
            key: selected.get(key)
            for key in (
                "format_id",
                "format_note",
                "ext",
                "width",
                "height",
                "fps",
                "vcodec",
                "acodec",
                "filesize",
                "filesize_approx",
            )
            if selected.get(key) is not None
        },
        "metadata": _metadata(info),
    }


def _resolve_with_metadata(
    input_str: str,
    format_id: Optional[str] = None,
    *,
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
    resolve_timeout: int = 180,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    page_url = normalize_input(input_str)
    info = _load_metadata(
        page_url,
        socket_timeout=socket_timeout,
        resolve_timeout=resolve_timeout,
    )
    selected = _select_format(info, requested_format_id=format_id)
    result = _public_info(info, page_url, selected)
    download_runtime.emit_status(
        "resolved",
        platform=PLATFORM,
        video_id=result.get("video_id"),
        format_id=result.get("format_id"),
        quality=result.get("quality"),
    )
    return result, selected, info


def _resolve(
    input_str: str,
    format_id: Optional[str] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, selected, _ = _resolve_with_metadata(input_str, format_id=format_id)
    return result, selected


def resolve_video_info(
    input_str: str,
    format_id: Optional[str] = None,
    *,
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
    resolve_timeout: int = 180,
) -> dict[str, Any]:
    result, _, _ = _resolve_with_metadata(
        input_str,
        format_id=format_id,
        socket_timeout=socket_timeout,
        resolve_timeout=resolve_timeout,
    )
    return result


def _resolve_output_dir(output_dir: Optional[str]) -> Path:
    return download_runtime.resolve_output_directory(output_dir).path


def download_with_info(
    input_str: str,
    output_dir: Optional[str] = None,
    format_id: Optional[str] = None,
    attempts: int = 3,
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
    resolve_timeout: int = 180,
    download_timeout: int = download_runtime.DEFAULT_DOWNLOAD_TIMEOUT,
    overall_timeout: int = download_runtime.DEFAULT_OVERALL_TIMEOUT,
) -> dict[str, Any]:
    output_decision = download_runtime.resolve_output_directory(output_dir)

    def operation(attempt: int, deadline: float) -> dict[str, Any]:
        resolved, selected, metadata = _resolve_with_metadata(
            input_str,
            format_id=format_id,
            socket_timeout=socket_timeout,
            resolve_timeout=download_runtime.bounded_timeout(resolve_timeout, deadline),
        )
        file_path, _ = download_runtime.download_from_metadata(
            base_command=_base_command(socket_timeout=socket_timeout),
            metadata=metadata,
            format_id=str(selected["format_id"]),
            selected_url=str(selected["url"]),
            output_directory=output_decision,
            output_template="youtube_%(id)s.%(ext)s",
            platform=PLATFORM,
            video_id=resolved.get("video_id"),
            timeout=download_runtime.bounded_timeout(download_timeout, deadline),
        )
        return {
            "file_path": str(file_path),
            "output_directory": output_decision.to_dict(),
            **resolved,
        }

    return download_runtime.execute_with_retries(
        operation,
        platform=PLATFORM,
        attempts=attempts,
        overall_timeout=overall_timeout,
    )


def download(
    input_str: str,
    output_dir: Optional[str] = None,
    format_id: Optional[str] = None,
    attempts: int = 3,
) -> str:
    return download_with_info(
        input_str,
        output_dir=output_dir,
        format_id=format_id,
        attempts=attempts,
    )["file_path"]


def check_environment() -> dict[str, Any]:
    missing: list[str] = []
    try:
        runner = _yt_dlp_runner()
        version = _run([*runner, "--version"], timeout=20).stdout.strip()
    except Exception as exc:
        runner = None
        version = None
        missing.append(str(exc))
    if sys.version_info < (3, 10):
        missing.append("Python 3.10 or newer is required.")
    return {
        "platform": PLATFORM,
        "python_supported": sys.version_info >= (3, 10),
        "yt_dlp_runner": runner,
        "yt_dlp_version": version,
        "player_client": PLAYER_CLIENT,
        "preferred_format_id": PREFERRED_FORMAT_ID,
        "fallback": "highest muxed MP4 exposed by the Android client",
        "default_attempts": 3,
        "default_socket_timeout": download_runtime.DEFAULT_SOCKET_TIMEOUT,
        "default_resolve_timeout": 180,
        "default_download_timeout": download_runtime.DEFAULT_DOWNLOAD_TIMEOUT,
        "default_overall_timeout": download_runtime.DEFAULT_OVERALL_TIMEOUT,
        "reads_user_config": False,
        "uses_browser_cookies": False,
        "uses_po_token": False,
        "downloads_subtitles": False,
        "supported_input": "youtube.com/watch?v=<11-character-video-id>",
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve or download a public YouTube watch video with yt-dlp's Android client."
    )
    parser.add_argument(
        "url_or_share_text",
        nargs="?",
        help="Public youtube.com/watch?v=<video_id> URL or share text containing one.",
    )
    parser.add_argument("--attempts", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument(
        "--socket-timeout",
        type=int,
        default=download_runtime.DEFAULT_SOCKET_TIMEOUT,
    )
    parser.add_argument("--resolve-timeout", type=int, default=180)
    parser.add_argument(
        "--download-timeout",
        type=int,
        default=download_runtime.DEFAULT_DOWNLOAD_TIMEOUT,
    )
    parser.add_argument(
        "--overall-timeout",
        type=int,
        default=download_runtime.DEFAULT_OVERALL_TIMEOUT,
    )
    parser.add_argument("--output-dir", help="Directory for downloaded MP4 files.")
    parser.add_argument(
        "--format-id",
        help="Optional muxed MP4 format ID. Defaults to format 18, then the best actual muxed MP4.",
    )
    parser.add_argument(
        "--print-url",
        action="store_true",
        help="Resolve metadata and the selected temporary media URL without downloading.",
    )
    parser.add_argument("--check", action="store_true", help="Check dependencies and exit.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    args = parser.parse_args()

    try:
        if args.check:
            data = check_environment()
        else:
            if not args.url_or_share_text:
                parser.error("url_or_share_text is required unless --check is used")
            if args.print_url:
                data = resolve_video_info(
                    args.url_or_share_text,
                    format_id=args.format_id,
                    socket_timeout=args.socket_timeout,
                    resolve_timeout=args.resolve_timeout,
                )
            else:
                data = download_with_info(
                    args.url_or_share_text,
                    output_dir=args.output_dir,
                    format_id=args.format_id,
                    attempts=args.attempts,
                    socket_timeout=args.socket_timeout,
                    resolve_timeout=args.resolve_timeout,
                    download_timeout=args.download_timeout,
                    overall_timeout=args.overall_timeout,
                )
        payload = _success(data)
        if args.json or args.check or args.print_url:
            _print_json(payload)
        else:
            print(data["file_path"])
        return 0
    except Exception as exc:
        payload = _failure(exc)
        if args.json:
            _print_json(payload)
        else:
            print(
                f"Download failed: {payload['error']}\nNext step: {payload['solution']}",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
