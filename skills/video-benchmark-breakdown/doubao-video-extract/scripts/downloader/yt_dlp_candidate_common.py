#!/usr/bin/env python3
"""Shared CLI adapter for public-video yt-dlp platform downloaders."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import download_runtime


URL_PATTERN = re.compile(r"https?://[^\s，。；;）)】>\]\"']+")
DEFAULT_FORMAT = "best"
DEFAULT_ATTEMPTS = 3


@dataclass(frozen=True)
class PlatformSpec:
    platform: str
    display_name: str
    description: str
    url_pattern: re.Pattern[str]
    input_help: str
    solution: str
    default_impersonate: Optional[str] = None


class YtDlpError(download_runtime.DownloadRuntimeError):
    def __init__(
        self,
        message: str,
        stderr: str = "",
        *,
        code: Optional[str] = None,
        stage: Optional[str] = None,
        retryable: Optional[bool] = None,
    ):
        inferred_code, inferred_retryable, inferred_stage = (
            download_runtime.classify_error(RuntimeError(f"{message}\n{stderr}"))
        )
        self.stderr = stderr
        super().__init__(
            message,
            code=code or inferred_code,
            stage=stage or inferred_stage,
            retryable=inferred_retryable if retryable is None else retryable,
            detail=stderr,
        )


def _success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def _failure(exc: Exception, solution: str) -> dict[str, Any]:
    return download_runtime.failure_payload(exc, solution)


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _extract_first_url(value: str) -> str:
    match = URL_PATTERN.search(html.unescape(value))
    if not match:
        raise ValueError("Input does not contain an http(s) URL.")
    return match.group(0)


def normalize_input(value: str, spec: PlatformSpec) -> str:
    url = _extract_first_url(value.strip())
    if not spec.url_pattern.fullmatch(url):
        raise ValueError(f"URL is not a supported {spec.display_name} URL: {url}")
    return url


def _yt_dlp_runner() -> list[str]:
    return download_runtime.discover_yt_dlp_runner()


def _yt_dlp_binary() -> str:
    """Compatibility accessor for callers that only need the leading executable."""
    return _yt_dlp_runner()[0]


def _run(
    command: list[str],
    *,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess[str]:
    stage = "resolve" if "--dump-single-json" in command else "preflight"
    effective_timeout = timeout or download_runtime.DEFAULT_DOWNLOAD_TIMEOUT
    try:
        return download_runtime.run_capture(
            command,
            timeout=effective_timeout,
            stage=stage,
        )
    except download_runtime.DownloadRuntimeError as exc:
        raise YtDlpError(
            str(exc),
            stderr=exc.detail,
            code=exc.code,
            stage=exc.stage,
            retryable=exc.retryable,
        ) from exc


def _base_command(
    spec: PlatformSpec,
    *,
    format_selector: str,
    impersonate: Optional[str],
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
) -> list[str]:
    command = [
        *_yt_dlp_runner(),
        *download_runtime.common_yt_dlp_options(
            socket_timeout=socket_timeout,
            retries=1,
            fragment_retries=1,
            extractor_retries=1,
        ),
        "--no-warnings",
        "--format",
        format_selector,
    ]
    selected_impersonate = impersonate or spec.default_impersonate
    if selected_impersonate:
        command.extend(["--impersonate", selected_impersonate])
    return command


def _compact_formats(info: dict[str, Any]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in info.get("formats") or []:
        if not isinstance(item, dict):
            continue
        selected = {
            key: item.get(key)
            for key in (
                "format_id",
                "ext",
                "width",
                "height",
                "fps",
                "vcodec",
                "acodec",
                "filesize",
                "filesize_approx",
                "tbr",
                "quality",
            )
            if item.get(key) is not None
        }
        if selected:
            compact.append(selected)
    return compact


def _metadata(info: dict[str, Any]) -> dict[str, Any]:
    statistics = {
        key: info.get(key)
        for key in (
            "view_count",
            "like_count",
            "comment_count",
            "repost_count",
        )
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
        "timestamp": info.get("timestamp"),
        "upload_date": info.get("upload_date"),
        "thumbnail": info.get("thumbnail"),
        "track": info.get("track"),
        "artist": info.get("artist"),
        "statistics": statistics,
        "available_formats": _compact_formats(info),
    }
    return {
        key: value
        for key, value in metadata.items()
        if value not in (None, "", {}, [])
    }


def _selected_download(info: dict[str, Any]) -> dict[str, Any]:
    requested = info.get("requested_downloads")
    if isinstance(requested, list) and requested and isinstance(requested[0], dict):
        return requested[0]
    return info


def _resolve(
    input_str: str,
    spec: PlatformSpec,
    *,
    format_selector: str = DEFAULT_FORMAT,
    impersonate: Optional[str] = None,
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
    resolve_timeout: int = download_runtime.DEFAULT_RESOLVE_TIMEOUT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    page_url = normalize_input(input_str, spec)
    download_runtime.emit_status("resolving", platform=spec.platform, page_url=page_url)
    command = _base_command(
        spec,
        format_selector=format_selector,
        impersonate=impersonate,
        socket_timeout=socket_timeout,
    )
    command.extend(["--skip-download", "--dump-single-json", page_url])
    completed = _run(command, timeout=resolve_timeout)
    try:
        info = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise YtDlpError(
            "yt-dlp returned invalid JSON.",
            stderr=completed.stdout[-1000:].strip(),
        ) from exc

    if not isinstance(info, dict):
        raise YtDlpError("yt-dlp returned an unexpected JSON value.")

    selected = _selected_download(info)
    video_url = selected.get("url") or info.get("url")
    if not video_url:
        raise YtDlpError("yt-dlp returned no selected media URL.")

    result = {
        "platform": spec.platform,
        "video_url": video_url,
        "video_id": info.get("id"),
        "page_url": info.get("webpage_url") or page_url,
        "format_id": selected.get("format_id") or info.get("format_id"),
        "quality": selected.get("format") or info.get("format"),
        "metadata": _metadata(info),
    }
    download_runtime.emit_status(
        "resolved",
        platform=spec.platform,
        video_id=result.get("video_id"),
        format_id=result.get("format_id"),
        quality=result.get("quality"),
    )
    return result, info, selected


def resolve_video_info(
    input_str: str,
    spec: PlatformSpec,
    *,
    format_selector: str = DEFAULT_FORMAT,
    impersonate: Optional[str] = None,
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
    resolve_timeout: int = download_runtime.DEFAULT_RESOLVE_TIMEOUT,
) -> dict[str, Any]:
    result, _, _ = _resolve(
        input_str,
        spec,
        format_selector=format_selector,
        impersonate=impersonate,
        socket_timeout=socket_timeout,
        resolve_timeout=resolve_timeout,
    )
    return result


def _resolve_output_dir(output_dir: Optional[str]) -> Path:
    return download_runtime.resolve_output_directory(output_dir).path


def download_with_info(
    input_str: str,
    spec: PlatformSpec,
    *,
    output_dir: Optional[str] = None,
    format_selector: str = DEFAULT_FORMAT,
    impersonate: Optional[str] = None,
    attempts: int = DEFAULT_ATTEMPTS,
    socket_timeout: int = download_runtime.DEFAULT_SOCKET_TIMEOUT,
    resolve_timeout: int = download_runtime.DEFAULT_RESOLVE_TIMEOUT,
    download_timeout: int = download_runtime.DEFAULT_DOWNLOAD_TIMEOUT,
    overall_timeout: int = download_runtime.DEFAULT_OVERALL_TIMEOUT,
) -> dict[str, Any]:
    output_decision = download_runtime.resolve_output_directory(output_dir)

    def operation(attempt: int, deadline: float) -> dict[str, Any]:
        resolved, metadata, selected = _resolve(
            input_str,
            spec,
            format_selector=format_selector,
            impersonate=impersonate,
            socket_timeout=socket_timeout,
            resolve_timeout=download_runtime.bounded_timeout(resolve_timeout, deadline),
        )
        file_path, _ = download_runtime.download_from_metadata(
            base_command=_base_command(
                spec,
                format_selector=format_selector,
                impersonate=impersonate,
                socket_timeout=socket_timeout,
            ),
            metadata=metadata,
            format_id=str(resolved["format_id"]),
            selected_url=str(selected.get("url") or resolved["video_url"]),
            output_directory=output_decision,
            output_template=f"{spec.platform}_%(id)s.%(ext)s",
            platform=spec.platform,
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
        platform=spec.platform,
        attempts=attempts,
        overall_timeout=overall_timeout,
    )


def check_environment(spec: PlatformSpec) -> dict[str, Any]:
    missing: list[str] = []
    try:
        runner = _yt_dlp_runner()
        version = _run([*runner, "--version"], timeout=20).stdout.strip()
    except Exception as exc:
        runner = None
        version = None
        missing.append(str(exc))

    impersonation_available: Optional[bool] = None
    if runner and spec.default_impersonate:
        try:
            targets = _run([*runner, "--list-impersonate-targets"], timeout=20).stdout
            impersonation_available = spec.default_impersonate.lower() in targets.lower()
        except Exception as exc:
            impersonation_available = False
            missing.append(str(exc))
        if not impersonation_available and not missing:
            missing.append(
                f"yt-dlp impersonation target {spec.default_impersonate!r} is unavailable"
            )

    return {
        "platform": spec.platform,
        "yt_dlp_binary": runner[0] if runner else None,
        "yt_dlp_runner": runner,
        "yt_dlp_version": version,
        "login_required": False,
        "reads_user_config": False,
        "supports_share_text": True,
        "default_format": DEFAULT_FORMAT,
        "default_attempts": DEFAULT_ATTEMPTS,
        "default_socket_timeout": download_runtime.DEFAULT_SOCKET_TIMEOUT,
        "default_resolve_timeout": download_runtime.DEFAULT_RESOLVE_TIMEOUT,
        "default_download_timeout": download_runtime.DEFAULT_DOWNLOAD_TIMEOUT,
        "default_overall_timeout": download_runtime.DEFAULT_OVERALL_TIMEOUT,
        "default_impersonate": spec.default_impersonate,
        "impersonation_available": impersonation_available,
        "missing": missing,
    }


def run_cli(spec: PlatformSpec) -> int:
    parser = argparse.ArgumentParser(description=spec.description)
    parser.add_argument(
        "url_or_share_text",
        nargs="?",
        help=spec.input_help,
    )
    parser.add_argument("--attempts", type=int, choices=(1, 2, 3), default=DEFAULT_ATTEMPTS)
    parser.add_argument(
        "--socket-timeout",
        type=int,
        default=download_runtime.DEFAULT_SOCKET_TIMEOUT,
    )
    parser.add_argument(
        "--resolve-timeout",
        type=int,
        default=download_runtime.DEFAULT_RESOLVE_TIMEOUT,
    )
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
    parser.add_argument(
        "--output-dir",
        help="Directory for downloaded files. Defaults to ./downloads.",
    )
    parser.add_argument(
        "--format",
        dest="format_selector",
        default=DEFAULT_FORMAT,
        help="yt-dlp format selector. Defaults to best.",
    )
    parser.add_argument(
        "--impersonate",
        help=(
            "Optional yt-dlp CLIENT[:OS] impersonation selector. "
            f"Platform default: {spec.default_impersonate or 'disabled'}."
        ),
    )
    parser.add_argument(
        "--print-url",
        action="store_true",
        help="Resolve and print structured media information without downloading.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    parser.add_argument("--check", action="store_true", help="Check dependencies and exit.")
    args = parser.parse_args()

    try:
        if args.check:
            payload = _success(check_environment(spec))
        else:
            if not args.url_or_share_text:
                parser.error("url_or_share_text is required unless --check is used")
            if args.print_url:
                data = resolve_video_info(
                    args.url_or_share_text,
                    spec,
                    format_selector=args.format_selector,
                    impersonate=args.impersonate,
                    socket_timeout=args.socket_timeout,
                    resolve_timeout=args.resolve_timeout,
                )
            else:
                data = download_with_info(
                    args.url_or_share_text,
                    spec,
                    output_dir=args.output_dir,
                    format_selector=args.format_selector,
                    impersonate=args.impersonate,
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
            print(payload["data"]["file_path"])
        return 0
    except Exception as exc:
        payload = _failure(exc, spec.solution)
        if args.json:
            _print_json(payload)
        else:
            print(
                f"Download failed: {payload['error']}\nNext step: {payload['solution']}",
                file=sys.stderr,
            )
        return 1
