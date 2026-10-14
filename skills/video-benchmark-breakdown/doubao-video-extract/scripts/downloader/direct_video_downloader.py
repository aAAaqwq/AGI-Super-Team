#!/usr/bin/env python3
"""Download a direct video file URL after validating it as video media."""

from __future__ import annotations

import argparse
import mimetypes
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "util"))

from script_utils import USER_AGENT, ensure_writable_dir, failure, normalize_share_input, print_json, success  # noqa: E402


PathLikeStr = Union[str, os.PathLike[str]]

VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".flv",
    ".mpeg",
    ".mpg",
    ".ts",
}

GENERIC_CONTENT_TYPES = {
    "",
    "application/octet-stream",
    "binary/octet-stream",
    "application/x-download",
}

CONTENT_TYPE_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
    "video/x-msvideo": ".avi",
    "video/x-flv": ".flv",
    "video/mpeg": ".mpg",
    "video/mp2t": ".ts",
}


def _resolve_output_dir(output_dir: Optional[PathLikeStr] = None) -> Path:
    configured_dir = output_dir or os.environ.get("VIDEO_EXTRACT_DOWNLOAD_DIR") or os.environ.get(
        "VIDEO_SUBTITLE_DOWNLOAD_DIR"
    )
    if configured_dir:
        return ensure_writable_dir(Path(configured_dir), fallback_name="downloads")
    return ensure_writable_dir(Path.cwd() / "downloads", fallback_name="downloads")


def _request_headers(range_header: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Accept": "*/*",
        "User-Agent": USER_AGENT,
    }
    if range_header:
        headers["Range"] = range_header
    return headers


def _normalize_url(input_str: str) -> str:
    url = normalize_share_input(input_str)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Direct video downloader requires an http(s) URL.")
    return url


def _url_extension(url: str) -> str:
    parsed = urlparse(url)
    return Path(unquote(parsed.path)).suffix.lower()


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return value or "video"


def _content_type(headers) -> str:
    raw_value = headers.get("Content-Type") or ""
    return raw_value.split(";", 1)[0].strip().lower()


def _content_length(headers) -> Optional[int]:
    raw_value = headers.get("Content-Length")
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _probe_url(url: str) -> dict[str, object]:
    normalized_url = _normalize_url(url)
    request = Request(normalized_url, headers=_request_headers(), method="HEAD")
    try:
        with urlopen(request, timeout=20) as response:
            final_url = response.geturl()
            content_type = _content_type(response.headers)
            content_length = _content_length(response.headers)
            return {
                "url": normalized_url,
                "final_url": final_url,
                "content_type": content_type,
                "content_length": content_length,
                "extension": _url_extension(final_url),
                "status": getattr(response, "status", None),
                "probe_method": "HEAD",
            }
    except Exception:
        request = Request(normalized_url, headers=_request_headers("bytes=0-0"))
        with urlopen(request, timeout=20) as response:
            final_url = response.geturl()
            content_type = _content_type(response.headers)
            content_length = _content_length(response.headers)
            return {
                "url": normalized_url,
                "final_url": final_url,
                "content_type": content_type,
                "content_length": content_length,
                "extension": _url_extension(final_url),
                "status": getattr(response, "status", None),
                "probe_method": "GET_RANGE",
            }


def is_video_probe(probe: dict[str, object]) -> bool:
    content_type = str(probe.get("content_type") or "").lower()
    extension = str(probe.get("extension") or "").lower()
    if content_type.startswith("video/"):
        return True
    return extension in VIDEO_EXTENSIONS and content_type in GENERIC_CONTENT_TYPES


def probe_video_url(url: str) -> dict[str, object]:
    probe = _probe_url(url)
    probe["is_video"] = is_video_probe(probe)
    return probe


def _extension_for_download(url: str, content_type: str) -> str:
    ext = _url_extension(url)
    if ext in VIDEO_EXTENSIONS:
        return ext
    if content_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[content_type]
    guessed = mimetypes.guess_extension(content_type)
    if guessed and guessed.lower() in VIDEO_EXTENSIONS:
        return guessed.lower()
    return ".mp4"


def _output_path(url: str, output_dir: Path, content_type: str) -> Path:
    parsed = urlparse(url)
    name = _safe_name(Path(unquote(parsed.path)).stem)
    ext = _extension_for_download(url, content_type)
    return output_dir / f"direct_{name}{ext}"


def _download_file(video_url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=str(output_path.parent),
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    try:
        request = Request(video_url, headers=_request_headers())
        with urlopen(request, timeout=60) as response, tmp_path.open("wb") as out_file:
            shutil.copyfileobj(response, out_file, length=1024 * 1024)
        tmp_path.replace(output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return output_path


def download(input_str: str, output_dir: Optional[PathLikeStr] = None) -> str:
    probe = probe_video_url(input_str)
    if not probe["is_video"]:
        raise ValueError(
            "URL does not look like a video file. Expected Content-Type video/* "
            f"or one of extensions {sorted(VIDEO_EXTENSIONS)}; got "
            f"content_type={probe.get('content_type')!r}, extension={probe.get('extension')!r}."
        )

    final_url = str(probe["final_url"])
    out_dir = _resolve_output_dir(output_dir)
    output_path = _output_path(final_url, out_dir, str(probe.get("content_type") or ""))
    saved_path = _download_file(final_url, output_path)

    abs_path = saved_path.resolve()
    if not abs_path.exists() or abs_path.stat().st_size == 0:
        raise FileNotFoundError(f"Downloaded file not found or empty: {abs_path}")
    return str(abs_path)


def check_environment() -> dict[str, object]:
    return {
        "direct_video_download": True,
        "video_extensions": sorted(VIDEO_EXTENSIONS),
        "video_content_types": ["video/*"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a direct video file URL.")
    parser.add_argument("url", help="Direct http(s) video file URL")
    parser.add_argument("--output-dir", help="Directory for downloaded files. Defaults to ./downloads.")
    parser.add_argument("--print-url", action="store_true", help="Validate and print the final URL without downloading.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    parser.add_argument("--check", action="store_true", help="Check URL classification and exit.")
    args = parser.parse_args()

    try:
        if args.check or args.print_url:
            probe = probe_video_url(args.url)
            if args.print_url and not probe["is_video"]:
                raise ValueError(f"URL is not classified as video: {probe}")
            payload = success({"platform": "direct", **probe})
        else:
            file_path = download(args.url, output_dir=args.output_dir)
            payload = success({"file_path": file_path, "platform": "direct"})

        if args.json or args.check or args.print_url:
            print_json(payload)
        else:
            print(payload["data"]["file_path"])
    except Exception as exc:
        payload = failure(
            exc,
            "Pass a direct http(s) URL whose response is video/* or whose path has a known video extension.",
        )
        if args.json:
            print_json(payload)
        else:
            print(f"Download failed: {payload['error']}\nNext step: {payload['solution']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
