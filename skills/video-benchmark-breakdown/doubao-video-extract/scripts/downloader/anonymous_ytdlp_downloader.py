#!/usr/bin/env python3
"""Shared anonymous yt-dlp runner for supported platform downloaders.

This module deliberately ignores user yt-dlp configuration and never loads
browser cookies, account credentials, or authentication tokens.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence
from urllib.parse import urlparse

import download_runtime


URL_PATTERN = re.compile(r"https?://[^\s，。；;）)】>\]\"']+")
VIDEO_EXTENSIONS = {"flv", "m4v", "mkv", "mov", "mp4", "ts", "webm"}
DEFAULT_ATTEMPTS = 3
DEFAULT_SOCKET_TIMEOUT = 20
DEFAULT_RESOLVE_TIMEOUT = 90
DEFAULT_DOWNLOAD_TIMEOUT = 1800
DEFAULT_OVERALL_TIMEOUT = 1800
MINIMUM_DURATION_RATIO = 0.9


@dataclass(frozen=True)
class PlatformConfig:
    platform: str
    display_name: str
    hosts: tuple[str, ...]
    extractor_keys: tuple[str, ...]
    minimum_python: tuple[int, int] = (3, 10)


class YtDlpCommandError(download_runtime.DownloadRuntimeError):
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


class IncompleteMediaError(RuntimeError):
    pass


class DownloadFailedError(RuntimeError):
    def __init__(self, message: str, failures: list[dict[str, Any]]):
        self.failures = failures
        self.error_code = failures[-1]["error_code"] if failures else "DOWNLOAD_FAILED"
        super().__init__(message)


def _success(data: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "data": data}


def _failure(exc: Exception, solution: str, attempts: list[dict[str, Any]]) -> dict[str, Any]:
    return download_runtime.failure_payload(
        exc,
        solution,
        attempts=attempts,
    )


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _emit_status(stage: str, **fields: Any) -> None:
    download_runtime.emit_status(stage, **fields)


def _normalize_input(value: str) -> str:
    match = URL_PATTERN.search(html.unescape(value.strip()))
    return (match.group(0) if match else value.strip()).rstrip(".,;，。；、")


def _host_matches(host: str, allowed: str) -> bool:
    return host == allowed or host.endswith(f".{allowed}")


def _validate_input(config: PlatformConfig, value: str) -> str:
    url = _normalize_input(value)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{config.display_name} input must contain an HTTP(S) video page URL.")
    host = parsed.netloc.lower().split(":", 1)[0]
    if not any(_host_matches(host, allowed) for allowed in config.hosts):
        raise ValueError(
            f"URL host {host!r} is not supported by the {config.display_name} candidate. "
            f"Expected one of {config.hosts}."
        )
    return url


def _yt_dlp_runner() -> Optional[list[str]]:
    try:
        return download_runtime.discover_yt_dlp_runner()
    except download_runtime.DownloadRuntimeError:
        return None


def _base_command(socket_timeout: int = DEFAULT_SOCKET_TIMEOUT) -> list[str]:
    runner = _yt_dlp_runner()
    if not runner:
        raise RuntimeError(
            "yt-dlp is unavailable. Install it in the active Python environment or expose "
            "the yt-dlp executable on PATH. The candidate script will not install it automatically."
        )
    return [
        *runner,
        *download_runtime.common_yt_dlp_options(socket_timeout=socket_timeout),
    ]


def _run(command: Sequence[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return download_runtime.run_capture(
            command,
            timeout=timeout,
            stage="resolve",
        )
    except download_runtime.DownloadRuntimeError as exc:
        raise YtDlpCommandError(
            str(exc),
            stderr=exc.detail,
            code=exc.code,
            stage=exc.stage,
            retryable=exc.retryable,
        ) from exc


def _run_streaming(command: Sequence[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return download_runtime.run_streaming(
            command,
            timeout=timeout,
            stage="download",
        )
    except download_runtime.DownloadRuntimeError as exc:
        raise YtDlpCommandError(
            str(exc),
            stderr=exc.detail,
            code=exc.code,
            stage=exc.stage,
            retryable=exc.retryable,
        ) from exc


def _extract_json(output: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("yt-dlp produced no JSON metadata object")


def _infer_height(item: dict[str, Any]) -> Optional[int]:
    height = item.get("height")
    if isinstance(height, (int, float)) and height > 0:
        return int(height)
    text = " ".join(
        str(item.get(key) or "")
        for key in ("resolution", "format_note", "format")
    )
    match = re.search(r"(?<!\d)(\d{3,4})[pP](?!\d)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"\b\d{2,5}x(\d{3,4})\b", text)
    return int(match.group(1)) if match else None


def _infer_width(item: dict[str, Any]) -> Optional[int]:
    width = item.get("width")
    if isinstance(width, (int, float)) and width > 0:
        return int(width)
    text = " ".join(str(item.get(key) or "") for key in ("resolution", "format"))
    match = re.search(r"\b(\d{2,5})x\d{3,4}\b", text)
    return int(match.group(1)) if match else None


def _format_candidates(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for source in metadata.get("formats") or []:
        if not isinstance(source, dict) or not source.get("format_id") or not source.get("url"):
            continue
        if source.get("has_drm") is True:
            continue
        if source.get("protocol") == "mhtml" or source.get("vcodec") == "none":
            continue
        extension = str(source.get("ext") or "").lower()
        height = _infer_height(source)
        if extension not in VIDEO_EXTENSIONS and height is None:
            continue
        item = dict(source)
        item["_height"] = height
        item["_width"] = _infer_width(source)
        candidates.append(item)
    return candidates


def _resolution_score(item: dict[str, Any]) -> tuple[int, int, float, int]:
    height = item.get("_height")
    width = item.get("_width")
    if height is None:
        return (1, sys.maxsize, float(item.get("tbr") or sys.maxsize), sys.maxsize)
    pixels = (width or height) * height
    size = item.get("filesize") or item.get("filesize_approx") or sys.maxsize
    return (0, pixels, float(item.get("tbr") or sys.maxsize), int(size))


def _select_format(
    candidates: list[dict[str, Any]],
    quality: str,
) -> dict[str, Any]:
    if not candidates:
        raise RuntimeError("yt-dlp returned no downloadable video formats")
    known = [item for item in candidates if item.get("_height") is not None]
    pool = known or candidates
    if quality == "lowest":
        return min(pool, key=_resolution_score)
    if quality == "best":
        return max(pool, key=_resolution_score)
    requested = int(quality.removesuffix("p"))
    exact = [item for item in known if item["_height"] == requested]
    if exact:
        return min(exact, key=_resolution_score)
    lower = [item for item in known if item["_height"] <= requested]
    if lower:
        return max(lower, key=_resolution_score)
    if known:
        return min(known, key=_resolution_score)
    return candidates[0]


def _same_resolution_candidates(
    candidates: list[dict[str, Any]],
    selected: dict[str, Any],
) -> list[dict[str, Any]]:
    identity_keys = (
        "_width",
        "_height",
        "ext",
        "vcodec",
        "acodec",
        "format_note",
    )
    selected_identity = tuple(selected.get(key) for key in identity_keys)
    matches = [
        item
        for item in candidates
        if tuple(item.get(key) for key in identity_keys) == selected_identity
    ]

    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any]] = set()
    for item in matches or [selected]:
        identity = (item.get("format_id"), item.get("url"))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(item)
    return result


def _metadata_for_selected_format(
    metadata: dict[str, Any],
    selected_format_id: str,
    selected_url: str,
) -> dict[str, Any]:
    return download_runtime.select_metadata_format(
        metadata,
        format_id=selected_format_id,
        selected_url=selected_url,
    )


def _available_resolutions(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in sorted(candidates, key=_resolution_score):
        identity = (
            item.get("_width"),
            item.get("_height"),
            item.get("format_note"),
        )
        if identity in seen:
            continue
        seen.add(identity)
        width = item.get("_width")
        height = item.get("_height")
        result.append(
            {
                "format_id": item.get("format_id"),
                "width": width,
                "height": height,
                "label": (
                    f"{width}x{height}"
                    if width and height
                    else item.get("format_note") or item.get("format") or "unknown"
                ),
            }
        )
    return result


def _resolution_range(available: list[dict[str, Any]]) -> dict[str, Optional[int]]:
    heights = sorted(
        {
            int(item["height"])
            for item in available
            if isinstance(item.get("height"), (int, float))
        }
    )
    return {
        "minimum_height": heights[0] if heights else None,
        "maximum_height": heights[-1] if heights else None,
    }


def _metadata_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    result = {
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "author": metadata.get("uploader") or metadata.get("creator"),
        "author_id": metadata.get("uploader_id") or metadata.get("channel_id"),
        "cover_url": metadata.get("thumbnail"),
        "duration": metadata.get("duration"),
        "timestamp": metadata.get("timestamp"),
        "view_count": metadata.get("view_count"),
        "like_count": metadata.get("like_count"),
        "comment_count": metadata.get("comment_count"),
    }
    return {key: value for key, value in result.items() if value not in (None, "", [], {})}


def _resolve_video_info_with_metadata(
    config: PlatformConfig,
    input_str: str,
    quality: str = "lowest",
    *,
    candidate_index: int = 0,
    resolve_timeout: int = DEFAULT_RESOLVE_TIMEOUT,
    socket_timeout: int = DEFAULT_SOCKET_TIMEOUT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    page_url = _validate_input(config, input_str)
    _emit_status("resolving", platform=config.platform, page_url=page_url)
    command = [
        *_base_command(socket_timeout=socket_timeout),
        "--simulate",
        "--skip-download",
        "--dump-single-json",
        page_url,
    ]
    metadata = _extract_json(_run(command, timeout=resolve_timeout).stdout)
    extractor = str(metadata.get("extractor_key") or metadata.get("extractor") or "")
    allowed_extractors = {value.casefold() for value in config.extractor_keys}
    if extractor.casefold() not in allowed_extractors:
        raise RuntimeError(
            f"Unexpected yt-dlp extractor {extractor!r}; expected one of {config.extractor_keys}. "
            "Refusing to rely on the Generic extractor."
        )

    candidates = _format_candidates(metadata)
    initially_selected = _select_format(candidates, quality=quality)
    mirrors = _same_resolution_candidates(candidates, initially_selected)
    selected_mirror_index = candidate_index % len(mirrors)
    selected = mirrors[selected_mirror_index]
    available = _available_resolutions(candidates)
    width = selected.get("_width")
    height = selected.get("_height")
    info = {
        "platform": config.platform,
        "page_url": metadata.get("webpage_url") or page_url,
        "video_id": metadata.get("id"),
        "video_url": selected["url"],
        "format_id": selected["format_id"],
        "quality": f"{width}x{height}" if width and height else selected.get("format_note") or "unknown",
        "selected_format": {
            "format_id": selected.get("format_id"),
            "width": width,
            "height": height,
            "format_note": selected.get("format_note"),
            "ext": selected.get("ext"),
            "protocol": selected.get("protocol"),
            "filesize": selected.get("filesize"),
            "filesize_approx": selected.get("filesize_approx"),
            "cdn_host": urlparse(str(selected.get("url") or "")).hostname,
        },
        "cdn_mirror_count": len(mirrors),
        "cdn_mirror_index": selected_mirror_index,
        "available_resolutions": available,
        "resolution_range": _resolution_range(available),
        "metadata": _metadata_fields(metadata),
    }
    _emit_status(
        "resolved",
        platform=config.platform,
        video_id=info.get("video_id"),
        quality=info.get("quality"),
        format_id=info.get("format_id"),
        cdn_mirror_index=selected_mirror_index,
        cdn_mirror_count=len(mirrors),
    )
    return info, metadata


def resolve_video_info(
    config: PlatformConfig,
    input_str: str,
    quality: str = "lowest",
    *,
    resolve_timeout: int = DEFAULT_RESOLVE_TIMEOUT,
    socket_timeout: int = DEFAULT_SOCKET_TIMEOUT,
) -> dict[str, Any]:
    info, _ = _resolve_video_info_with_metadata(
        config,
        input_str,
        quality=quality,
        resolve_timeout=resolve_timeout,
        socket_timeout=socket_timeout,
    )
    return info


def _resolve_output_dir(output_dir: Optional[str]) -> Path:
    return download_runtime.resolve_output_directory(output_dir).path


def _probe_media(path: Path) -> dict[str, Any]:
    try:
        import av  # type: ignore
    except Exception:
        return {
            "available": False,
            "reason": "PyAV is unavailable; file existence and yt-dlp exit status were checked only.",
        }
    with av.open(str(path)) as container:
        video_streams = [stream for stream in container.streams if stream.type == "video"]
        audio_streams = [stream for stream in container.streams if stream.type == "audio"]
        if not video_streams:
            raise RuntimeError("downloaded file contains no video stream")
        frame = next(container.decode(video=video_streams[0].index), None)
        if frame is None:
            raise RuntimeError("unable to decode the first video frame")
        duration = (
            round(container.duration / av.time_base, 3)
            if container.duration is not None
            else None
        )
        return {
            "available": True,
            "width": frame.width,
            "height": frame.height,
            "duration": duration,
            "has_audio": bool(audio_streams),
            "size_bytes": path.stat().st_size,
        }


def _validate_duration(info: dict[str, Any], probe: dict[str, Any]) -> None:
    expected = info.get("metadata", {}).get("duration")
    actual = probe.get("duration")
    if not probe.get("available") or not expected or not actual:
        return
    if float(actual) < float(expected) * MINIMUM_DURATION_RATIO:
        raise IncompleteMediaError(
            f"downloaded media is incomplete: actual duration {actual}s is below "
            f"{MINIMUM_DURATION_RATIO:.0%} of expected duration {expected}s"
        )


def _download_once(
    config: PlatformConfig,
    input_str: str,
    output_dir: Optional[str],
    quality: str,
    *,
    candidate_index: int = 0,
    resolve_timeout: int = DEFAULT_RESOLVE_TIMEOUT,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
    socket_timeout: int = DEFAULT_SOCKET_TIMEOUT,
    deadline: Optional[float] = None,
) -> dict[str, Any]:
    output_decision = download_runtime.resolve_output_directory(output_dir)
    target_dir = output_decision.path
    _emit_status("initialized", platform=config.platform, output_dir=str(target_dir))
    info, metadata = _resolve_video_info_with_metadata(
        config,
        input_str,
        quality=quality,
        candidate_index=candidate_index,
        resolve_timeout=(
            _bounded_timeout(resolve_timeout, deadline)
            if deadline is not None
            else resolve_timeout
        ),
        socket_timeout=socket_timeout,
    )
    template = (
        f"{config.platform}_%(id)s_%(height)sp.%(ext)s"
    )
    effective_download_timeout = (
        _bounded_timeout(download_timeout, deadline)
        if deadline is not None
        else download_timeout
    )
    file_path, _ = download_runtime.download_from_metadata(
        base_command=_base_command(socket_timeout=socket_timeout),
        metadata=metadata,
        format_id=str(info["format_id"]),
        selected_url=str(info["video_url"]),
        output_directory=output_decision,
        output_template=template,
        platform=config.platform,
        video_id=info.get("video_id"),
        timeout=effective_download_timeout,
    )

    _emit_status("verifying", platform=config.platform, file_path=str(file_path))
    probe = _probe_media(file_path)
    _validate_duration(info, probe)
    info["file_path"] = str(file_path)
    info["output_directory"] = output_decision.to_dict()
    info["verification"] = probe
    if probe.get("available"):
        available = info["available_resolutions"]
        actual = {
            "format_id": info["format_id"],
            "width": probe.get("width"),
            "height": probe.get("height"),
            "label": f"{probe.get('width')}x{probe.get('height')}",
        }
        if not any(
            item.get("width") == actual["width"] and item.get("height") == actual["height"]
            for item in available
        ):
            available.append(actual)
        info["resolution_range"] = _resolution_range(available)
    _emit_status(
        "completed",
        platform=config.platform,
        file_path=str(file_path),
        size_bytes=file_path.stat().st_size,
    )
    return info


def _classify_failure(exc: Exception) -> tuple[str, bool]:
    code, retryable, _ = download_runtime.classify_error(exc)
    return code, retryable


def _bounded_timeout(requested: int, deadline: float) -> int:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise YtDlpCommandError("overall download timeout exceeded")
    return max(1, min(requested, int(remaining + 0.999)))


def download_with_info(
    config: PlatformConfig,
    input_str: str,
    output_dir: Optional[str] = None,
    quality: str = "lowest",
    attempts: int = DEFAULT_ATTEMPTS,
    *,
    resolve_timeout: int = DEFAULT_RESOLVE_TIMEOUT,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
    socket_timeout: int = DEFAULT_SOCKET_TIMEOUT,
    overall_timeout: int = DEFAULT_OVERALL_TIMEOUT,
) -> dict[str, Any]:
    if attempts < 1 or attempts > 3:
        raise ValueError("attempts must be between 1 and 3")
    for name, value in (
        ("resolve_timeout", resolve_timeout),
        ("download_timeout", download_timeout),
        ("socket_timeout", socket_timeout),
        ("overall_timeout", overall_timeout),
    ):
        if value < 1:
            raise ValueError(f"{name} must be at least 1 second")
    failures: list[dict[str, Any]] = []
    deadline = time.monotonic() + overall_timeout
    for attempt in range(1, attempts + 1):
        try:
            result = _download_once(
                config,
                input_str,
                output_dir,
                quality,
                candidate_index=attempt - 1,
                resolve_timeout=resolve_timeout,
                download_timeout=download_timeout,
                socket_timeout=socket_timeout,
                deadline=deadline,
            )
            result["successful_attempt"] = attempt
            if failures:
                result["previous_failures"] = failures
            return result
        except Exception as exc:
            error_code, retryable = _classify_failure(exc)
            if time.monotonic() >= deadline:
                error_code = "OVERALL_TIMEOUT"
                retryable = False
            failures.append(
                {
                    "attempt": attempt,
                    "error": f"{type(exc).__name__}: {exc}",
                    "error_code": error_code,
                    "retryable": retryable,
                }
            )
            _emit_status(
                "attempt_failed",
                platform=config.platform,
                attempt=attempt,
                error_code=error_code,
                retryable=retryable,
            )
            if not retryable or attempt >= attempts:
                break
            backoff = min(attempt * 2, max(0, deadline - time.monotonic()))
            if backoff <= 0:
                break
            _emit_status(
                "retrying",
                platform=config.platform,
                next_attempt=attempt + 1,
                delay_seconds=round(backoff, 3),
            )
            time.sleep(backoff)
    raise DownloadFailedError(
        f"{config.display_name} download failed after {len(failures)} attempt(s)",
        failures,
    )


def check_environment(config: PlatformConfig) -> dict[str, Any]:
    runner = _yt_dlp_runner()
    pyav_available = importlib.util.find_spec("av") is not None
    missing = []
    yt_dlp_version = None
    if runner:
        try:
            yt_dlp_version = download_runtime.run_capture(
                [*runner, "--version"],
                timeout=20,
                stage="preflight",
            ).stdout.strip()
        except Exception as exc:
            missing.append(str(exc))
    else:
        missing.append("yt-dlp")
    if sys.version_info < config.minimum_python:
        missing.append(f"Python {config.minimum_python[0]}.{config.minimum_python[1]}+")
    return {
        "platform": config.platform,
        "candidate_only": False,
        "anonymous_mode": True,
        "ignores_yt_dlp_config": True,
        "uses_browser_cookies": False,
        "yt_dlp_runner": runner,
        "yt_dlp_available": bool(runner),
        "yt_dlp_version": yt_dlp_version,
        "pyav_available": pyav_available,
        "python_supported": sys.version_info >= config.minimum_python,
        "minimum_python": ".".join(str(part) for part in config.minimum_python),
        "default_quality": "lowest",
        "default_attempts": DEFAULT_ATTEMPTS,
        "default_socket_timeout": DEFAULT_SOCKET_TIMEOUT,
        "default_resolve_timeout": DEFAULT_RESOLVE_TIMEOUT,
        "default_download_timeout": DEFAULT_DOWNLOAD_TIMEOUT,
        "default_overall_timeout": DEFAULT_OVERALL_TIMEOUT,
        "missing": missing,
    }


def _solution(config: PlatformConfig, exc: Exception) -> str:
    message = str(exc).lower()
    if "cookie" in message or "login" in message:
        return (
            "This candidate is anonymous-only. The input requires cookies or login and is "
            "outside the supported scope."
        )
    if "429" in message or "too many requests" in message:
        return "The platform rate-limited anonymous requests. Wait before trying again."
    if "incomplete" in message:
        return "The platform returned only a preview or partial stream; do not treat it as success."
    return (
        f"Confirm the URL is a public {config.display_name} video, inspect --print-url --json, "
        "and do not add cookies, account credentials, or private tokens."
    )


def run_cli(config: PlatformConfig) -> int:
    parser = argparse.ArgumentParser(
        description=f"Resolve or download a public {config.display_name} video anonymously via yt-dlp."
    )
    parser.add_argument("input", nargs="?", help=f"{config.display_name} page URL or share text")
    parser.add_argument("--output-dir", help="Directory for downloaded media")
    parser.add_argument(
        "--quality",
        default="lowest",
        choices=("lowest", "best", "1080p", "720p", "576p", "540p", "480p", "360p", "270p"),
        help="Resolution selection. Defaults to the lowest exposed video format.",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=DEFAULT_ATTEMPTS,
        choices=(1, 2, 3),
        help="Maximum attempts. Stops immediately after the first success.",
    )
    parser.add_argument(
        "--socket-timeout",
        type=int,
        default=DEFAULT_SOCKET_TIMEOUT,
        help=f"Network socket timeout in seconds. Defaults to {DEFAULT_SOCKET_TIMEOUT}.",
    )
    parser.add_argument(
        "--resolve-timeout",
        type=int,
        default=DEFAULT_RESOLVE_TIMEOUT,
        help=f"Metadata resolution timeout in seconds. Defaults to {DEFAULT_RESOLVE_TIMEOUT}.",
    )
    parser.add_argument(
        "--download-timeout",
        type=int,
        default=DEFAULT_DOWNLOAD_TIMEOUT,
        help=f"Single download attempt timeout in seconds. Defaults to {DEFAULT_DOWNLOAD_TIMEOUT}.",
    )
    parser.add_argument(
        "--overall-timeout",
        type=int,
        default=DEFAULT_OVERALL_TIMEOUT,
        help=f"Overall retry budget in seconds. Defaults to {DEFAULT_OVERALL_TIMEOUT}.",
    )
    parser.add_argument("--print-url", action="store_true", help="Resolve metadata and media URL only")
    parser.add_argument("--check", action="store_true", help="Check dependencies without network access")
    parser.add_argument("--json", action="store_true", help="Print structured JSON")
    args = parser.parse_args()

    try:
        if args.check:
            result = check_environment(config)
        else:
            if not args.input:
                parser.error("input is required unless --check is used")
            if args.print_url:
                result = resolve_video_info(
                    config,
                    args.input,
                    quality=args.quality,
                    resolve_timeout=args.resolve_timeout,
                    socket_timeout=args.socket_timeout,
                )
            else:
                result = download_with_info(
                    config,
                    args.input,
                    output_dir=args.output_dir,
                    quality=args.quality,
                    attempts=args.attempts,
                    resolve_timeout=args.resolve_timeout,
                    download_timeout=args.download_timeout,
                    socket_timeout=args.socket_timeout,
                    overall_timeout=args.overall_timeout,
                )
        if args.json:
            _print_json(_success(result))
        elif args.print_url:
            print(result["video_url"])
        elif args.check:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["file_path"])
        return 0
    except Exception as exc:
        attempts = getattr(exc, "failures", [])
        payload = _failure(exc, _solution(config, exc), attempts)
        if args.json:
            _print_json(payload)
        else:
            print(
                f"Download failed: {payload['error']}\nNext step: {payload['solution']}",
                file=sys.stderr,
            )
        return 1
