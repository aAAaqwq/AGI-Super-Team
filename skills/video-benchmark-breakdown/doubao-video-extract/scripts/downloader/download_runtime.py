"""Shared download runtime for video platform adapters."""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence


DEFAULT_SOCKET_TIMEOUT = 20
DEFAULT_RESOLVE_TIMEOUT = 120
DEFAULT_DOWNLOAD_TIMEOUT = 1800
DEFAULT_OVERALL_TIMEOUT = 1800


class DownloadRuntimeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "DOWNLOAD_FAILED",
        stage: str = "download",
        retryable: bool = True,
        detail: str = "",
    ):
        self.code = code
        self.stage = stage
        self.retryable = retryable
        self.detail = detail
        self.stderr = detail
        super().__init__(message)


class DownloadAttemptsError(DownloadRuntimeError):
    def __init__(
        self,
        message: str,
        *,
        attempts: list[dict[str, Any]],
        code: str,
        stage: str,
        retryable: bool,
    ):
        self.attempts = attempts
        super().__init__(
            message,
            code=code,
            stage=stage,
            retryable=retryable,
        )


@dataclass(frozen=True)
class OutputDirectoryDecision:
    requested: str
    actual: str
    fallback_used: bool
    fallback_reason: Optional[str] = None

    @property
    def path(self) -> Path:
        return Path(self.actual)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "actual": self.actual,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
        }


def emit_status(stage: str, **fields: Any) -> None:
    payload = {
        "event": "video_extract_status",
        "stage": stage,
        **{key: value for key, value in fields.items() if value is not None},
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)


def classify_error(exc: Exception, stage: str = "download") -> tuple[str, bool, str]:
    if isinstance(exc, DownloadRuntimeError):
        return exc.code, exc.retryable, exc.stage
    legacy_code = getattr(exc, "error_code", None)
    legacy_attempts = getattr(exc, "failures", None) or getattr(exc, "attempts", None)
    if legacy_code:
        last_attempt = legacy_attempts[-1] if legacy_attempts else {}
        return (
            str(legacy_code),
            bool(last_attempt.get("retryable", False)),
            str(last_attempt.get("stage") or stage),
        )
    message = str(exc).lower()
    if isinstance(exc, ValueError):
        return "INVALID_INPUT", False, "input"
    if isinstance(exc, FileNotFoundError):
        if any(marker in message for marker in ("yt-dlp", "pyav", "lark-cli", "executable")):
            return "DEPENDENCY_MISSING", False, "preflight"
        return "FILE_NOT_FOUND", False, stage
    if isinstance(exc, PermissionError):
        return "PERMISSION_DENIED", False, "output"
    if "timed out" in message or "timeout" in message:
        return "TIMEOUT", True, stage
    if any(
        marker in message
        for marker in (
            "cookie",
            "login",
            "member",
            "paid",
            "private",
            "drm",
            "geo",
            "age-restricted",
            "region-restricted",
        )
    ):
        return "ACCESS_RESTRICTED", False, "resolve"
    if "unexpected yt-dlp extractor" in message:
        return "EXTRACTOR_CHANGED", False, "resolve"
    if any(
        marker in message
        for marker in (
            "video unavailable",
            "not available",
            "deleted",
            "no downloadable",
            "unsupported url",
        )
    ):
        return "VIDEO_UNAVAILABLE", False, "resolve"
    if "429" in message or "too many requests" in message:
        return "RATE_LIMITED", True, stage
    if "403" in message or "forbidden" in message:
        return "CDN_FORBIDDEN", True, stage
    if any(marker in message for marker in ("incomplete", "empty", "decode", "no completed media")):
        return "MEDIA_INCOMPLETE", True, "verify"
    if isinstance(exc, OSError):
        return "OUTPUT_ERROR", False, "output"
    return "DOWNLOAD_FAILED", True, stage


def failure_payload(
    exc: Exception,
    next_action: str = "",
    *,
    stage: str = "download",
    attempts: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    code, retryable, resolved_stage = classify_error(exc, stage=stage)
    detail = getattr(exc, "detail", "") or getattr(exc, "stderr", "")
    recorded_attempts = attempts
    if recorded_attempts is None:
        recorded_attempts = getattr(exc, "attempts", None) or getattr(exc, "failures", [])
    payload: dict[str, Any] = {
        "success": False,
        "error": str(exc),
        "error_code": code,
        "error_type": type(exc).__name__,
        "stage": resolved_stage,
        "retryable": retryable,
        "next_action": next_action,
        "solution": next_action,
        "attempts": recorded_attempts or [],
    }
    if detail:
        payload["detail"] = str(detail)
    return payload


def discover_yt_dlp_runner(*, allow_module: bool = True) -> list[str]:
    configured = os.environ.get("YT_DLP_BIN")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise DownloadRuntimeError(
                f"YT_DLP_BIN is not executable: {path}",
                code="DEPENDENCY_MISSING",
                stage="preflight",
                retryable=False,
            )
        return [str(path.resolve())]
    if allow_module:
        try:
            import importlib.util

            if importlib.util.find_spec("yt_dlp") is not None:
                return [sys.executable, "-m", "yt_dlp"]
        except Exception:
            pass
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]
    raise DownloadRuntimeError(
        "yt-dlp is not installed in the active Python environment or available on PATH.",
        code="DEPENDENCY_MISSING",
        stage="preflight",
        retryable=False,
    )


def common_yt_dlp_options(
    *,
    socket_timeout: int = DEFAULT_SOCKET_TIMEOUT,
    retries: int = 0,
    fragment_retries: int = 0,
    extractor_retries: int = 0,
) -> list[str]:
    if socket_timeout < 1:
        raise ValueError("socket_timeout must be at least 1 second")
    return [
        "--ignore-config",
        "--no-playlist",
        "--socket-timeout",
        str(socket_timeout),
        "--retries",
        str(retries),
        "--fragment-retries",
        str(fragment_retries),
        "--extractor-retries",
        str(extractor_retries),
    ]


def run_capture(
    command: Sequence[str],
    *,
    timeout: int,
    stage: str,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise DownloadRuntimeError(
            f"yt-dlp timed out after {timeout} seconds",
            code="TIMEOUT",
            stage=stage,
            retryable=True,
            detail=(exc.stderr or "").strip(),
        ) from exc
    if completed.returncode:
        detail_lines = [line.strip() for line in completed.stderr.splitlines() if line.strip()]
        detail = " | ".join(detail_lines[-6:])
        code, retryable, _ = classify_error(RuntimeError(detail), stage=stage)
        raise DownloadRuntimeError(
            detail or f"yt-dlp exited with status {completed.returncode}",
            code=code,
            stage=stage,
            retryable=retryable,
            detail=detail,
        )
    return completed


def run_streaming(
    command: Sequence[str],
    *,
    timeout: int,
    stage: str = "download",
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_queue: queue.Queue[Optional[str]] = queue.Queue()

    def read_output() -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                output_queue.put(line)
        finally:
            output_queue.put(None)

    reader = threading.Thread(target=read_output, name="yt-dlp-output", daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    output_lines: list[str] = []
    stream_closed = False
    try:
        while not stream_closed or process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                raise DownloadRuntimeError(
                    f"yt-dlp timed out after {timeout} seconds",
                    code="TIMEOUT",
                    stage=stage,
                    retryable=True,
                )
            try:
                line = output_queue.get(timeout=min(0.25, remaining))
            except queue.Empty:
                continue
            if line is None:
                stream_closed = True
                continue
            output_lines.append(line)
            print(line.rstrip("\n"), file=sys.stderr, flush=True)
    finally:
        reader.join(timeout=1)

    return_code = process.wait()
    output = "".join(output_lines)
    if return_code:
        detail_lines = [line.strip() for line in output.splitlines() if line.strip()]
        detail = " | ".join(detail_lines[-6:])
        code, retryable, _ = classify_error(RuntimeError(detail), stage=stage)
        raise DownloadRuntimeError(
            detail or f"yt-dlp exited with status {return_code}",
            code=code,
            stage=stage,
            retryable=retryable,
            detail=detail,
        )
    return subprocess.CompletedProcess(list(command), return_code, output, "")


def progress_options() -> list[str]:
    return [
        "--progress",
        "--newline",
        "--no-colors",
        "--progress-template",
        (
            'download:{"event":"download_progress",'
            '"status":"%(progress.status)s",'
            '"downloaded_bytes":"%(progress.downloaded_bytes)s",'
            '"total_bytes":"%(progress.total_bytes)s",'
            '"speed":"%(progress.speed)s",'
            '"eta":"%(progress.eta)s",'
            '"percent":"%(progress._percent_str)s"}'
        ),
    ]


def bounded_timeout(requested: int, deadline: float) -> int:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise DownloadRuntimeError(
            "Overall download timeout exceeded",
            code="OVERALL_TIMEOUT",
            stage="download",
            retryable=False,
        )
    return max(1, min(requested, int(remaining + 0.999)))


def execute_with_retries(
    operation,
    *,
    platform: str,
    attempts: int = 3,
    overall_timeout: int = DEFAULT_OVERALL_TIMEOUT,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if overall_timeout < 1:
        raise ValueError("overall_timeout must be at least 1 second")
    deadline = time.monotonic() + overall_timeout
    failures: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        try:
            result = operation(attempt, deadline)
            if isinstance(result, dict):
                result["successful_attempt"] = attempt
                if failures:
                    result["previous_failures"] = failures
            return result
        except Exception as exc:
            code, retryable, stage = classify_error(exc)
            if time.monotonic() >= deadline:
                code = "OVERALL_TIMEOUT"
                retryable = False
            failure = {
                "attempt": attempt,
                "error": f"{type(exc).__name__}: {exc}",
                "error_code": code,
                "stage": stage,
                "retryable": retryable,
            }
            failures.append(failure)
            emit_status(
                "attempt_failed",
                platform=platform,
                attempt=attempt,
                error_code=code,
                error_stage=stage,
                retryable=retryable,
            )
            if not retryable or attempt >= attempts:
                raise DownloadAttemptsError(
                    f"{platform} download failed after {len(failures)} attempt(s)",
                    attempts=failures,
                    code=code,
                    stage=stage,
                    retryable=retryable,
                ) from exc
            delay = min(attempt * 2, max(0, deadline - time.monotonic()))
            if delay <= 0:
                raise DownloadAttemptsError(
                    f"{platform} download exceeded the overall timeout",
                    attempts=failures,
                    code="OVERALL_TIMEOUT",
                    stage="download",
                    retryable=False,
                ) from exc
            emit_status(
                "retrying",
                platform=platform,
                next_attempt=attempt + 1,
                delay_seconds=round(delay, 3),
            )
            time.sleep(delay)


def _writable_directory(path: Path) -> Optional[str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
            return f"Directory is not writable: {path}"
        probe = path / ".video-extract-write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def resolve_output_directory(
    output_dir: Optional[str],
    *,
    default_name: str = "downloads",
    allow_fallback: bool = True,
) -> OutputDirectoryDecision:
    configured = (
        output_dir
        or os.environ.get("VIDEO_EXTRACT_DOWNLOAD_DIR")
        or os.environ.get("VIDEO_SUBTITLE_DOWNLOAD_DIR")
    )
    requested_path = (
        Path(configured).expanduser().resolve()
        if configured
        else (Path.cwd() / default_name).resolve()
    )
    reason = _writable_directory(requested_path)
    if reason is None:
        return OutputDirectoryDecision(
            requested=str(requested_path),
            actual=str(requested_path),
            fallback_used=False,
        )
    if not allow_fallback:
        raise DownloadRuntimeError(
            reason,
            code="OUTPUT_ERROR",
            stage="output",
            retryable=False,
        )

    fallback_candidates = [
        (Path.home() / ".cache" / "video-extract" / default_name).resolve(),
        (Path(tempfile.gettempdir()) / "video-extract" / default_name).resolve(),
    ]
    for candidate in fallback_candidates:
        candidate_reason = _writable_directory(candidate)
        if candidate_reason is None:
            decision = OutputDirectoryDecision(
                requested=str(requested_path),
                actual=str(candidate),
                fallback_used=True,
                fallback_reason=reason,
            )
            emit_status("output_fallback", **decision.to_dict())
            return decision
    raise DownloadRuntimeError(
        f"No writable output directory. Requested path failed: {reason}",
        code="OUTPUT_ERROR",
        stage="output",
        retryable=False,
    )


def select_metadata_format(
    metadata: dict[str, Any],
    *,
    format_id: str,
    selected_url: Optional[str] = None,
) -> dict[str, Any]:
    selected_formats = [
        dict(item)
        for item in metadata.get("formats") or []
        if isinstance(item, dict)
        and str(item.get("format_id")) == str(format_id)
        and (selected_url is None or str(item.get("url")) == selected_url)
    ]
    if not selected_formats:
        raise DownloadRuntimeError(
            "Selected format disappeared from resolved metadata",
            code="EXTRACTOR_CHANGED",
            stage="resolve",
            retryable=False,
        )
    result = dict(metadata)
    result["formats"] = selected_formats
    result.pop("requested_downloads", None)
    result.pop("requested_formats", None)
    return result


def download_from_metadata(
    *,
    base_command: Sequence[str],
    metadata: dict[str, Any],
    format_id: str,
    selected_url: Optional[str],
    output_directory: OutputDirectoryDecision,
    output_template: str,
    platform: str,
    video_id: Optional[str],
    timeout: int,
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    selected_metadata = select_metadata_format(
        metadata,
        format_id=format_id,
        selected_url=selected_url,
    )
    metadata_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".info.json",
            delete=False,
        ) as metadata_file:
            json.dump(selected_metadata, metadata_file, ensure_ascii=False)
            metadata_path = Path(metadata_file.name)
        command = [
            *base_command,
            "--load-info-json",
            str(metadata_path),
            "--format",
            str(format_id),
            "--paths",
            output_directory.actual,
            "--output",
            output_template,
            *progress_options(),
            "--print",
            "after_move:filepath",
        ]
        emit_status(
            "downloading",
            platform=platform,
            video_id=video_id,
            output_dir=output_directory.actual,
        )
        completed = run_streaming(command, timeout=timeout, stage="download")
    finally:
        if metadata_path is not None:
            metadata_path.unlink(missing_ok=True)

    candidates = [
        Path(line.strip()).expanduser().resolve()
        for line in completed.stdout.splitlines()
        if line.strip() and Path(line.strip()).expanduser().is_file()
    ]
    if not candidates:
        fallback = sorted(
            output_directory.path.glob(f"{platform}_{video_id or '*'}*"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        candidates = [path.resolve() for path in fallback if path.is_file()]
    if not candidates:
        raise DownloadRuntimeError(
            "yt-dlp completed without reporting a downloaded file path",
            code="MEDIA_INCOMPLETE",
            stage="verify",
            retryable=True,
        )
    file_path = candidates[-1] if completed.stdout.splitlines() else candidates[0]
    if file_path.stat().st_size <= 0:
        raise DownloadRuntimeError(
            f"Downloaded file is empty: {file_path}",
            code="MEDIA_INCOMPLETE",
            stage="verify",
            retryable=True,
        )
    return file_path, completed
