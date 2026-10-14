#!/usr/bin/env python3
"""Download a video, optionally extract audio, and hand off to Lark Minutes.

By default this script performs only local work and prints the Lark commands to run.
Use --run-lark to execute drive upload, minutes generation, and vc notes retrieval.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILL_ROOT = SCRIPTS_DIR.parent
for module_dir in ("convert", "downloader", "util", "video_extract"):
    sys.path.insert(0, str(SCRIPTS_DIR / module_dir))

import acfun_downloader
import anonymous_ytdlp_downloader
import bilibili_downloader
import cctv_downloader
import convert_video_to_audio
import direct_video_downloader
import doubao_transcript_doc
import estimate_lark_minutes_wait
import facebook_reels_downloader
import instagram_reels_downloader
import kuaishou_downloader
import mgtv_downloader
import pearvideo_downloader
import sohu_downloader
import tencent_video_downloader
import tiktok_downloader
import twitch_clips_downloader
import weibo_downloader
import x_downloader
import youtube_downloader
import yt_dlp_candidate_common
import download_runtime
from script_utils import check_executable, normalize_share_input, resolve_short_video_url


ANONYMOUS_YTDLP_DOWNLOADERS = {
    "acfun": acfun_downloader,
    "cctv": cctv_downloader,
    "mgtv": mgtv_downloader,
    "pearvideo": pearvideo_downloader,
    "sohu": sohu_downloader,
    "tencent_video": tencent_video_downloader,
}

SPEC_YTDLP_DOWNLOADERS = {
    "facebook_reels": facebook_reels_downloader,
    "instagram_reels": instagram_reels_downloader,
    "tiktok": tiktok_downloader,
    "twitch_clips": twitch_clips_downloader,
    "x": x_downloader,
}

YT_DLP_PLATFORMS = {
    *ANONYMOUS_YTDLP_DOWNLOADERS,
    *SPEC_YTDLP_DOWNLOADERS,
    "youtube",
}


class UnsupportedWebsiteError(ValueError):
    pass


class OnlineSourceRequiresAudioError(ValueError):
    pass


def _unsupported_website_message(host: str) -> str:
    return "抱歉，不支持解析该网站的视频"


def _detect_platform(input_str: str) -> str:
    input_str = resolve_short_video_url(normalize_share_input(input_str))
    if Path(input_str).expanduser().is_file():
        return "local"
    parsed = urlparse(input_str)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    value = input_str.strip()
    if value.startswith("1034:"):
        return "weibo"
    if "bilibili.com" in host or value.upper().startswith("BV") or _is_av_id(value):
        return "bilibili"
    if (
        host == "douyin.com"
        or host.endswith(".douyin.com")
        or host == "iesdouyin.com"
        or host.endswith(".iesdouyin.com")
    ):
        raise UnsupportedWebsiteError(_unsupported_website_message(host))
    if "kuaishou.com" in host or "kwaicdn.com" in host:
        return "kuaishou"
    if host == "acfun.cn" or host.endswith(".acfun.cn"):
        return "acfun"
    if host in {"tv.cctv.com", "cntv.cn"} or host.endswith(".cntv.cn"):
        return "cctv"
    if host == "mgtv.com" or host.endswith(".mgtv.com"):
        return "mgtv"
    if host == "pearvideo.com" or host.endswith(".pearvideo.com"):
        return "pearvideo"
    if host in {"tv.sohu.com", "my.tv.sohu.com"}:
        return "sohu"
    if host == "v.qq.com":
        return "tencent_video"
    if (host == "facebook.com" or host.endswith(".facebook.com")) and path.startswith("/reel/"):
        return "facebook_reels"
    if (host == "instagram.com" or host.endswith(".instagram.com")) and path.startswith("/reel/"):
        return "instagram_reels"
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return "tiktok"
    if host == "clips.twitch.tv" or (
        (host == "twitch.tv" or host.endswith(".twitch.tv")) and "/clip/" in path
    ):
        return "twitch_clips"
    if host in {
        "x.com",
        "www.x.com",
        "mobile.x.com",
        "twitter.com",
        "www.twitter.com",
        "mobile.twitter.com",
    } and re.fullmatch(r"/[^/]+/status/\d+(?:/video/\d+)?/?", path):
        return "x"
    if host in {"weibo.com", "www.weibo.com", "h5.video.weibo.com"} and "/show/" in path:
        return "weibo"
    if (host == "youtube.com" or host.endswith(".youtube.com")) and path.rstrip("/") == "/watch":
        return "youtube"
    if parsed.scheme in {"http", "https"}:
        try:
            probe = direct_video_downloader.probe_video_url(input_str)
        except Exception:
            probe = {"is_video": False}
        if probe.get("is_video"):
            return "direct"
        raise UnsupportedWebsiteError(_unsupported_website_message(host))
    raise ValueError(
        "Unable to detect platform. Pass an existing local video file or use --platform "
        "with one of the supported platform names."
    )


def _resolve_local_video(input_str: str) -> str:
    path = Path(input_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Local video file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Local video input is not a file: {path}")
    if path.suffix.lower() not in direct_video_downloader.VIDEO_EXTENSIONS:
        raise ValueError(
            f"Unsupported local video extension {path.suffix!r}. Expected one of "
            f"{sorted(direct_video_downloader.VIDEO_EXTENSIONS)}."
        )
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Local video file is not readable: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Local video file is empty: {path}")
    return str(path)


def _validate_lark_upload_policy(platform: str, media_mode: str) -> None:
    if platform != "local" and media_mode != "audio":
        raise OnlineSourceRequiresAudioError(
            "Online video sources must be converted to audio before uploading to Lark Minutes; "
            "video uploads are only allowed for local files."
        )


def _prepare_media(
    video_path: str,
    platform: str,
    media_mode: str,
    audio_output_dir: Optional[str],
    audio_format: str,
    overwrite_audio: bool,
) -> tuple[str, str, Optional[str]]:
    if media_mode == "video":
        return video_path, "video", None

    try:
        audio_path = convert_video_to_audio.convert_video_to_audio(
            video_path,
            output_dir=audio_output_dir,
            audio_format=audio_format,
            overwrite=overwrite_audio,
        )
        return audio_path, "audio", None
    except Exception as exc:
        if platform != "local":
            raise OnlineSourceRequiresAudioError(
                "Audio conversion failed for an online video source: "
                f"{type(exc).__name__}: {exc}. Refusing to upload the video file."
            ) from exc
        return video_path, "video", str(exc)


def _download_video(
    platform: str,
    input_str: str,
    output_dir: str,
    *,
    quality: str = "lowest",
    attempts: int = anonymous_ytdlp_downloader.DEFAULT_ATTEMPTS,
    resolve_timeout: int = anonymous_ytdlp_downloader.DEFAULT_RESOLVE_TIMEOUT,
    download_timeout: int = anonymous_ytdlp_downloader.DEFAULT_DOWNLOAD_TIMEOUT,
    socket_timeout: int = anonymous_ytdlp_downloader.DEFAULT_SOCKET_TIMEOUT,
    overall_timeout: int = anonymous_ytdlp_downloader.DEFAULT_OVERALL_TIMEOUT,
) -> Any:
    if platform == "bilibili":
        return bilibili_downloader.download(input_str, output_dir=output_dir)
    if platform == "kuaishou":
        return kuaishou_downloader.download(input_str, output_dir=output_dir)
    if platform == "direct":
        return direct_video_downloader.download(input_str, output_dir=output_dir)
    if platform == "weibo":
        return weibo_downloader.download_with_info(input_str, output_dir=output_dir)
    if platform == "youtube":
        return youtube_downloader.download_with_info(
            input_str,
            output_dir=output_dir,
            attempts=attempts,
            socket_timeout=socket_timeout,
            resolve_timeout=resolve_timeout,
            download_timeout=download_timeout,
            overall_timeout=overall_timeout,
        )
    if platform in ANONYMOUS_YTDLP_DOWNLOADERS:
        module = ANONYMOUS_YTDLP_DOWNLOADERS[platform]
        result = anonymous_ytdlp_downloader.download_with_info(
            module.CONFIG,
            input_str,
            output_dir=output_dir,
            quality=quality,
            attempts=attempts,
            resolve_timeout=resolve_timeout,
            download_timeout=download_timeout,
            socket_timeout=socket_timeout,
            overall_timeout=overall_timeout,
        )
        return result
    if platform in SPEC_YTDLP_DOWNLOADERS:
        module = SPEC_YTDLP_DOWNLOADERS[platform]
        result = yt_dlp_candidate_common.download_with_info(
            input_str,
            module.SPEC,
            output_dir=output_dir,
            attempts=attempts,
            socket_timeout=socket_timeout,
            resolve_timeout=resolve_timeout,
            download_timeout=download_timeout,
            overall_timeout=overall_timeout,
        )
        return result
    raise ValueError(f"Unsupported platform: {platform}")


def _resolve_source_info(platform: str, input_str: str) -> Optional[dict[str, Any]]:
    if platform == "bilibili":
        play = bilibili_downloader.get_playurl_with_fallback(input_str)
        return {
            "platform": "bilibili",
            "url": play["url"],
            "video_url": play["url"],
            "cid": play["cid"],
            "page": play["page"],
            "quality": play["quality"],
            "quality_label": play["quality_label"],
            "metadata": play.get("metadata", {}),
            "pages": play.get("pages", []),
        }
    if platform == "kuaishou":
        return kuaishou_downloader.resolve_video_info(input_str)
    if platform == "weibo":
        return weibo_downloader.resolve_video_info(input_str)
    if platform == "youtube":
        return youtube_downloader.resolve_video_info(input_str)
    if platform in ANONYMOUS_YTDLP_DOWNLOADERS:
        module = ANONYMOUS_YTDLP_DOWNLOADERS[platform]
        return anonymous_ytdlp_downloader.resolve_video_info(module.CONFIG, input_str)
    if platform in SPEC_YTDLP_DOWNLOADERS:
        module = SPEC_YTDLP_DOWNLOADERS[platform]
        return yt_dlp_candidate_common.resolve_video_info(input_str, module.SPEC)
    return None


def _is_av_id(input_str: str) -> bool:
    value = input_str.strip()
    return value.lower().startswith("av") and value[2:].isdigit()


def _normalize_video_input(input_str: str) -> str:
    return resolve_short_video_url(normalize_share_input(input_str))


def _extract_json_object(output: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError(f"No JSON object found in command output: {output}")


def _find_value(node: Any, key: str) -> Optional[str]:
    if isinstance(node, dict):
        value = node.get(key)
        if isinstance(value, str) and value:
            return value
        for child in node.values():
            found = _find_value(child, key)
            if found:
                return found
    elif isinstance(node, list):
        for child in node:
            found = _find_value(child, key)
            if found:
                return found
    return None


def _run_json_command(command: list[str], cwd: Optional[Path] = None) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, text=True, capture_output=True, cwd=cwd)
    return _extract_json_object(completed.stdout)


class LarkAuthorizationError(RuntimeError):
    def __init__(self, stage: str, output: str):
        self.stage = stage
        self.output = output
        super().__init__(
            "Lark authorization failed. Report the authorization issue; do not use third-party transcription tools."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "authorization_failed",
            "stage": self.stage,
            "next_action": "report_lark_authorization_issue",
            "output": self.output,
        }


def _is_lark_authorization_error(output: str) -> bool:
    lowered = output.lower()
    markers = (
        "invalid access token",
        "access token",
        "unauthorized",
        "authorization",
        "permission denied",
        "missing scope",
        "scope",
        "token expired",
        "needs_refresh",
    )
    return any(marker in lowered for marker in markers)


def _run_lark_json_command(stage: str, command: list[str], cwd: Optional[Path] = None) -> dict[str, Any]:
    try:
        return _run_json_command(command, cwd=cwd)
    except subprocess.CalledProcessError as exc:
        output = f"{exc.stdout or ''}\n{exc.stderr or ''}".strip()
        if _is_lark_authorization_error(output):
            raise LarkAuthorizationError(stage, output) from exc
        raise


def check_environment(
    input_str: str,
    platform: str,
    media_mode: str,
    audio_output_dir: Optional[str] = None,
    run_lark: bool = False,
) -> dict[str, Any]:
    dependency_manifest_path = SKILL_ROOT / "dependencies.json"
    dependency_manifest = json.loads(
        dependency_manifest_path.read_text(encoding="utf-8")
    )
    checks: dict[str, Any] = {
        "input": {
            "normalized": _normalize_video_input(input_str),
            "platform": platform,
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "stdlib": str(Path(os.__file__).resolve().parents[1]),
        },
        "dependencies": {
            "required": {},
            "optional": {},
            "not_needed": ["ffmpeg", "ffprobe"],
        },
        "dependency_manifest": {
            "path": str(dependency_manifest_path),
            "schema_version": dependency_manifest.get("schema_version"),
            "policy": dependency_manifest.get("policy", {}),
        },
    }
    if run_lark:
        lark_cli = check_executable("lark-cli")
        checks["dependencies"]["required"]["lark_cli"] = lark_cli
    else:
        checks["dependencies"]["not_needed"].append("lark_cli")
        lark_cli = None
    if lark_cli and lark_cli["available"]:
        version_process = subprocess.run(
            ["lark-cli", "--version"],
            text=True,
            capture_output=True,
        )
        lark_cli["version_output"] = (
            version_process.stdout or version_process.stderr
        ).strip()
    if platform == "kuaishou":
        checks["downloader"] = kuaishou_downloader.check_environment()
    elif platform == "bilibili":
        checks["downloader"] = bilibili_downloader.check_environment()
    elif platform == "direct":
        checks["downloader"] = direct_video_downloader.check_environment()
        try:
            checks["direct_url_probe"] = direct_video_downloader.probe_video_url(input_str)
        except Exception as exc:
            checks["direct_url_probe"] = {
                "success": False,
                "error": str(exc),
            }
    elif platform == "weibo":
        checks["downloader"] = weibo_downloader.check_environment()
    elif platform == "youtube":
        checks["downloader"] = youtube_downloader.check_environment()
    elif platform in ANONYMOUS_YTDLP_DOWNLOADERS:
        module = ANONYMOUS_YTDLP_DOWNLOADERS[platform]
        checks["downloader"] = anonymous_ytdlp_downloader.check_environment(module.CONFIG)
    elif platform in SPEC_YTDLP_DOWNLOADERS:
        module = SPEC_YTDLP_DOWNLOADERS[platform]
        checks["downloader"] = yt_dlp_candidate_common.check_environment(module.SPEC)
    elif platform == "local":
        local_path = Path(_resolve_local_video(input_str))
        checks["local_file"] = {
            "path": str(local_path),
            "exists": True,
            "readable": True,
            "extension": local_path.suffix.lower(),
            "size_bytes": local_path.stat().st_size,
        }

    if platform in YT_DLP_PLATFORMS:
        downloader_check = checks.get("downloader", {})
        yt_dlp_version = downloader_check.get("yt_dlp_version")
        yt_dlp_runner = (
            downloader_check.get("yt_dlp_runner")
            or downloader_check.get("yt_dlp_binary")
        )
        checks["dependencies"]["required"]["yt_dlp"] = {
            "available": bool(yt_dlp_runner),
            "runner": yt_dlp_runner,
            "version": yt_dlp_version,
            "version_policy": dependency_manifest["dependencies"]["yt-dlp"][
                "version_policy"
            ],
        }
    else:
        checks["dependencies"]["not_needed"].append("yt_dlp")

    if media_mode == "audio":
        fallback_note = (
            "Audio mode uses PyAV to generate a compressed MP3 file by default. "
            "If PyAV conversion fails, local video inputs may fall back to uploading the source MP4; "
            "online video sources must stop instead of uploading video."
        )
        audio_backends = convert_video_to_audio.check_backends()
        pyav = audio_backends.get("pyav", {"available": False})
        checks["dependencies"]["required"]["pyav"] = {
            **pyav,
            "purpose": "audio_conversion",
        }
        checks["audio_conversion"] = {
            "backend": "pyav",
            "backends": audio_backends,
            "output_dir": _audio_output_dir_check(input_str, platform, audio_output_dir),
            "note": fallback_note,
        }
    else:
        pyav = convert_video_to_audio.check_backends().get(
            "pyav",
            {"available": False},
        )
        checks["dependencies"]["optional"]["pyav"] = {
            **pyav,
            "purpose": "media_verification",
        }

    return checks


def _check_task_dependencies(
    platform: str,
    media_mode: str,
    run_lark: bool,
) -> None:
    if platform in YT_DLP_PLATFORMS:
        download_runtime.discover_yt_dlp_runner()

    if platform != "local" and media_mode == "audio":
        pyav = convert_video_to_audio.check_backends().get(
            "pyav",
            {"available": False},
        )
        if not pyav.get("available"):
            raise download_runtime.DownloadRuntimeError(
                "PyAV is required to convert online video to audio.",
                code="DEPENDENCY_MISSING",
                stage="preflight",
                retryable=False,
                detail=str(pyav.get("error") or ""),
            )

    if run_lark:
        lark_cli = check_executable("lark-cli")
        if not lark_cli.get("available"):
            raise download_runtime.DownloadRuntimeError(
                "lark-cli is required when --run-lark is enabled.",
                code="DEPENDENCY_MISSING",
                stage="preflight",
                retryable=False,
            )


def _audio_output_dir_check(
    input_str: str,
    platform: str,
    audio_output_dir: Optional[str],
) -> dict[str, Any]:
    if audio_output_dir:
        output_path = Path(audio_output_dir).expanduser().resolve()
        strategy = "explicit"
    elif platform == "local":
        output_path = Path(_resolve_local_video(input_str)).parent
        strategy = "input_media_parent"
    else:
        return {
            "strategy": "downloaded_video_parent",
            "path": None,
            "writable": None,
            "note": "The converted audio will use the downloader's final video directory.",
        }

    existing_path = output_path
    while not existing_path.exists() and existing_path != existing_path.parent:
        existing_path = existing_path.parent

    if output_path.exists() and not output_path.is_dir():
        writable = False
        reason = "Path exists but is not a directory."
    else:
        writable = existing_path.is_dir() and os.access(existing_path, os.W_OK | os.X_OK)
        reason = None if writable else f"Directory is not writable: {existing_path}"

    result: dict[str, Any] = {
        "strategy": strategy,
        "path": str(output_path),
        "exists": output_path.exists(),
        "writable": writable,
    }
    if not output_path.exists():
        result["existing_parent"] = str(existing_path)
    if reason:
        result["reason"] = reason
    return result


def _extract_minute_token(minute_url: str) -> str:
    parsed = urlparse(minute_url)
    token = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    if not token:
        raise ValueError(f"Unable to extract minute token from URL: {minute_url}")
    return token


def _drive_upload_spec(media_path: str) -> dict[str, Any]:
    media = Path(media_path).expanduser().resolve()
    return {
        "cwd": str(media.parent),
        "argv": [
            "lark-cli",
            "drive",
            "+upload",
            "--file",
            f"./{media.name}",
            "--format",
            "json",
        ],
    }


def _lark_commands(media_path: str, notes_output_dir: str, overwrite_notes: bool) -> dict[str, Any]:
    drive_command = _drive_upload_spec(media_path)
    drive_command = [
        *drive_command["argv"],
    ]
    minutes_command = [
        "lark-cli",
        "minutes",
        "+upload",
        "--file-token",
        "<file_token>",
        "--format",
        "json",
    ]
    notes_command = [
        "lark-cli",
        "vc",
        "+notes",
        "--minute-tokens",
        "<minute_token>",
        "--output-dir",
        notes_output_dir,
        "--format",
        "json",
    ]
    if overwrite_notes:
        notes_command.append("--overwrite")
    return {
        "drive_upload": {
            "cwd": str(Path(media_path).expanduser().resolve().parent),
            "argv": drive_command,
        },
        "minutes_upload": {"cwd": str(Path.cwd().resolve()), "argv": minutes_command},
        "vc_notes": {"cwd": str(Path.cwd().resolve()), "argv": notes_command},
    }


def _notes_not_ready(notes_result: dict[str, Any]) -> bool:
    notes = notes_result.get("data", {}).get("notes", [])
    for note in notes:
        error = str(note.get("error", "")).lower()
        if "not ready" in error or "try later" in error:
            return True
    return False


def _find_transcript_artifacts(notes_output_dir: str, minute_token: str) -> dict[str, Any]:
    output_root = Path(notes_output_dir).expanduser().resolve()
    if not output_root.exists():
        return {"transcript_files": [], "artifact_files": []}

    candidate_roots = [output_root / minute_token, output_root]
    transcript_files: list[str] = []
    artifact_files: list[str] = []
    seen: set[Path] = set()
    for root in candidate_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            resolved = path.resolve()
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            if path.name == "transcript.txt":
                transcript_files.append(str(resolved))
            artifact_files.append(str(resolved))

    return {
        "transcript_files": transcript_files,
        "transcript_file": transcript_files[0] if transcript_files else None,
        "artifact_files": artifact_files,
    }


def _write_default_doubao_doc(
    artifacts: dict[str, Any],
    *,
    media_path: str,
    minute_url: str,
    source_url: Optional[str],
) -> dict[str, Any]:
    transcript_file = artifacts.get("transcript_file")
    if not transcript_file:
        return {}
    transcript_path = Path(str(transcript_file)).expanduser().resolve()
    output_path = transcript_path.with_name("doubao_transcript.md")
    rendered = doubao_transcript_doc.write_doubao_transcript_doc(
        transcript_path,
        output_path,
        source_url=source_url,
        media_path=media_path,
        minute_url=minute_url,
    )
    return {
        "doubao_doc_file": rendered,
        "doubao_doc_format": "markdown",
    }


def _run_lark(
    media_path: str,
    notes_output_dir: str,
    overwrite_notes: bool,
    notes_retries: int,
    notes_wait: int,
    source_url: Optional[str] = None,
) -> dict[str, Any]:
    if source_url and Path(media_path).suffix.lower() in direct_video_downloader.VIDEO_EXTENSIONS:
        raise OnlineSourceRequiresAudioError(
            "Online video sources must be converted to audio before uploading to Lark Minutes; "
            "refusing to upload the video file."
        )
    commands = _lark_commands(media_path, notes_output_dir, overwrite_notes)
    try:
        wait_estimate = estimate_lark_minutes_wait.estimate_from_media(
            media_path,
            notes_retries=notes_retries,
            notes_wait_seconds=notes_wait,
        )
    except Exception as exc:
        wait_estimate = {
            "error": str(exc),
            "notes_retries": notes_retries,
            "notes_wait_seconds": notes_wait,
        }

    drive_result = _run_lark_json_command(
        "drive_upload",
        commands["drive_upload"]["argv"],
        cwd=Path(commands["drive_upload"]["cwd"]),
    )
    file_token = _find_value(drive_result, "file_token")
    if not file_token:
        raise ValueError(f"Unable to find file_token in drive upload response: {drive_result}")

    minutes_command = [
        value if value != "<file_token>" else file_token for value in commands["minutes_upload"]["argv"]
    ]
    minutes_result = _run_lark_json_command(
        "minutes_upload",
        minutes_command,
        cwd=Path(commands["minutes_upload"]["cwd"]),
    )
    minute_url = _find_value(minutes_result, "minute_url")
    if not minute_url:
        raise ValueError(f"Unable to find minute_url in minutes upload response: {minutes_result}")

    minute_token = _extract_minute_token(minute_url)
    notes_command = [
        value if value != "<minute_token>" else minute_token for value in commands["vc_notes"]["argv"]
    ]

    last_error = None
    notes_result: Optional[dict[str, Any]] = None
    for attempt in range(notes_retries + 1):
        try:
            notes_result = _run_lark_json_command(
                "vc_notes",
                notes_command,
                cwd=Path(commands["vc_notes"]["cwd"]),
            )
            if not _notes_not_ready(notes_result):
                break
            last_error = RuntimeError("minute not ready, try later")
            if attempt >= notes_retries:
                break
            time.sleep(notes_wait)
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if attempt >= notes_retries:
                raise
            time.sleep(notes_wait)

    artifacts = _find_transcript_artifacts(notes_output_dir, minute_token)
    doubao_doc_artifacts = _write_default_doubao_doc(
        artifacts,
        media_path=media_path,
        minute_url=minute_url,
        source_url=source_url,
    )
    ready_state = "ready"
    status = "success"
    if notes_result is not None and _notes_not_ready(notes_result):
        ready_state = "processing"
        status = "processing_with_transcript" if artifacts["transcript_files"] else "processing"

    return {
        "status": status,
        "ready_state": ready_state,
        "file_token": file_token,
        "minute_url": minute_url,
        "minute_token": minute_token,
        **artifacts,
        **doubao_doc_artifacts,
        "wait_estimate": wait_estimate,
        "drive_upload": drive_result,
        "minutes_upload": minutes_result,
        "vc_notes": notes_result,
        "last_notes_error": str(last_error) if last_error else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare an online or local video and optionally run Lark Minutes transcription."
    )
    parser.add_argument(
        "url_or_id",
        help="Local video path, platform URL, direct video URL, share text, or supported video ID",
    )
    parser.add_argument(
        "--platform",
        choices=[
            "auto",
            "acfun",
            "bilibili",
            "cctv",
            "direct",
            "facebook_reels",
            "instagram_reels",
            "kuaishou",
            "local",
            "mgtv",
            "pearvideo",
            "sohu",
            "tencent_video",
            "tiktok",
            "twitch_clips",
            "weibo",
            "x",
            "youtube",
        ],
        default="auto",
        help="Source platform. Defaults to auto detection.",
    )
    parser.add_argument(
        "--output-dir",
        default=(
            os.environ.get("VIDEO_EXTRACT_DOWNLOAD_DIR")
            or os.environ.get("VIDEO_SUBTITLE_DOWNLOAD_DIR")
            or "downloads"
        ),
        help="Directory for downloaded videos. Defaults to downloads.",
    )
    parser.add_argument(
        "--quality",
        default="lowest",
        choices=("lowest", "best", "1080p", "720p", "576p", "540p", "480p", "360p", "270p"),
        help="Resolution for shared anonymous downloaders. Defaults to lowest.",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        choices=(1, 2, 3),
        default=anonymous_ytdlp_downloader.DEFAULT_ATTEMPTS,
        help="Maximum download attempts. Defaults to 3.",
    )
    parser.add_argument(
        "--socket-timeout",
        type=int,
        default=anonymous_ytdlp_downloader.DEFAULT_SOCKET_TIMEOUT,
        help="Network socket timeout in seconds. Defaults to 20.",
    )
    parser.add_argument(
        "--resolve-timeout",
        type=int,
        default=anonymous_ytdlp_downloader.DEFAULT_RESOLVE_TIMEOUT,
        help="Metadata resolution timeout in seconds. Defaults to 90.",
    )
    parser.add_argument(
        "--download-timeout",
        type=int,
        default=anonymous_ytdlp_downloader.DEFAULT_DOWNLOAD_TIMEOUT,
        help="Single download attempt timeout in seconds. Defaults to 1800.",
    )
    parser.add_argument(
        "--overall-timeout",
        type=int,
        default=anonymous_ytdlp_downloader.DEFAULT_OVERALL_TIMEOUT,
        help="Overall download and retry budget in seconds. Defaults to 1800.",
    )
    parser.add_argument(
        "--audio-output-dir",
        help="Directory for converted audio. Defaults to the downloaded or local video's directory.",
    )
    parser.add_argument(
        "--media-mode",
        choices=["audio", "video"],
        default="audio",
        help="Prepare audio or video. Online sources require audio for Lark uploads; video uploads are local-only.",
    )
    parser.add_argument(
        "--audio-format",
        choices=["mp3", "wav"],
        default="mp3",
        help="Converted audio format. Defaults to mp3.",
    )
    parser.add_argument("--overwrite-audio", action="store_true", help="Overwrite converted audio.")
    parser.add_argument(
        "--run-lark",
        action="store_true",
        help="Execute lark-cli drive upload, minutes upload, and vc notes retrieval.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check input and local dependencies; do not download.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON output. Kept for a stable unified preflight command.")
    parser.add_argument(
        "--notes-output-dir",
        default="minutes",
        help="Output directory for vc +notes transcript artifacts. Defaults to minutes.",
    )
    parser.add_argument("--overwrite-notes", action="store_true", help="Overwrite existing notes files.")
    parser.add_argument(
        "--notes-retries",
        type=int,
        default=10,
        help="Retries for vc +notes while Lark Minutes is still processing. Defaults to 10.",
    )
    parser.add_argument(
        "--notes-wait",
        type=int,
        default=30,
        help="Seconds to wait between vc +notes retries. Defaults to 30.",
    )
    args = parser.parse_args()

    try:
        normalized_input = _normalize_video_input(args.url_or_id)
        platform = _detect_platform(normalized_input) if args.platform == "auto" else args.platform

        if args.run_lark:
            _validate_lark_upload_policy(platform, args.media_mode)

        if args.check:
            print(
                json.dumps(
                    {
                        "success": True,
                        "data": check_environment(
                            normalized_input,
                            platform,
                            args.media_mode,
                            args.audio_output_dir,
                            args.run_lark,
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        _check_task_dependencies(platform, args.media_mode, args.run_lark)

        source_info = None
        source_info_error = None
        if platform == "local":
            video_path = _resolve_local_video(normalized_input)
        else:
            download_result = _download_video(
                platform,
                normalized_input,
                args.output_dir,
                quality=args.quality,
                attempts=args.attempts,
                resolve_timeout=args.resolve_timeout,
                download_timeout=args.download_timeout,
                socket_timeout=args.socket_timeout,
                overall_timeout=args.overall_timeout,
            )
            if isinstance(download_result, dict):
                video_path = str(download_result["file_path"])
                source_info = download_result
            else:
                video_path = str(download_result)
        if platform != "local" and source_info is None:
            try:
                source_info = _resolve_source_info(platform, normalized_input)
            except Exception as exc:
                source_info_error = str(exc)

        media_path, effective_media_mode, audio_fallback_reason = _prepare_media(
            video_path,
            platform,
            args.media_mode,
            args.audio_output_dir,
            args.audio_format,
            args.overwrite_audio,
        )
        actual_output_dir = str(Path(video_path).resolve().parent)
        if platform == "local":
            output_directory = {
                "requested": actual_output_dir,
                "actual": actual_output_dir,
                "fallback_used": False,
                "fallback_reason": None,
            }
        else:
            requested_output_dir = str(Path(args.output_dir).expanduser().resolve())
            output_directory = (
                source_info.get("output_directory")
                if source_info
                else None
            ) or {
                "requested": requested_output_dir,
                "actual": actual_output_dir,
                "fallback_used": requested_output_dir != actual_output_dir,
                "fallback_reason": (
                    "Downloader selected a writable fallback directory."
                    if requested_output_dir != actual_output_dir
                    else None
                ),
            }
        result: dict[str, Any] = {
            "success": True,
            "platform": platform,
            "video_path": str(Path(video_path).resolve()),
            "file_path": str(Path(video_path).resolve()),
            "output_dir": actual_output_dir,
            "output_directory": output_directory,
            "requested_media_mode": args.media_mode,
            "media_mode": effective_media_mode,
            "audio_backend": "pyav" if args.media_mode == "audio" else None,
            "audio_fallback_reason": audio_fallback_reason,
            "media_path": str(Path(media_path).resolve()),
        }
        if platform == "local" or effective_media_mode == "audio":
            result["lark_commands"] = _lark_commands(
                media_path,
                args.notes_output_dir,
                args.overwrite_notes,
            )
        if source_info:
            result["source_info"] = source_info
            result["metadata"] = source_info.get("metadata", {})
            if source_info.get("quality") is not None:
                result["selected_quality"] = source_info.get("quality")
            if source_info.get("successful_attempt") is not None:
                result["attempts"] = source_info.get("successful_attempt")
            if platform in ANONYMOUS_YTDLP_DOWNLOADERS:
                result["requested_quality"] = args.quality
                result["verification"] = source_info.get("verification")
        elif source_info_error:
            result["source_info_error"] = source_info_error
        if args.run_lark:
            result["lark_result"] = _run_lark(
                media_path,
                args.notes_output_dir,
                args.overwrite_notes,
                args.notes_retries,
                args.notes_wait,
                source_url=None if platform == "local" else normalized_input,
            )

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        if isinstance(exc, UnsupportedWebsiteError):
            print(str(exc))
            return 1
        if isinstance(exc, LarkAuthorizationError):
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": str(exc),
                        "data": exc.to_dict(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        if isinstance(
            exc,
            (
                anonymous_ytdlp_downloader.DownloadFailedError,
                download_runtime.DownloadRuntimeError,
            ),
        ):
            payload = download_runtime.failure_payload(exc)
            print(
                json.dumps(payload, ensure_ascii=False, indent=2)
            )
            return 1
        if not isinstance(exc, OnlineSourceRequiresAudioError):
            print(
                json.dumps(
                    download_runtime.failure_payload(exc),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        print(
            "Social video to minutes failed: "
            f"{exc}\nNext step: run with --check, verify the local file path, pass --platform "
            "explicitly, or install missing downloader dependencies.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
