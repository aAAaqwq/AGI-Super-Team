#!/usr/bin/env python3
"""Resolve and download public Weibo videos through the mobile H5 component API.

This downloader is self-contained and uses only Python's standard library.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional, Union
from urllib.error import HTTPError
from urllib.parse import unquote
from urllib.request import Request, urlopen

import download_runtime


PathLikeStr = Union[str, os.PathLike[str]]

PLATFORM = "weibo"
COMPONENT_NAME = "Component_Play_Playinfo"
COMPONENT_API = "https://h5.video.weibo.com/api/component"
DEFAULT_QUALITY = "480p"
QUALITY_CHOICES = ("best", "1080p", "720p", "480p", "360p")
REFRESHABLE_DOWNLOAD_STATUS = {403, 410}
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4 Mobile/15E148 Safari/604.1"
)
DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
URL_PATTERN = re.compile(r"https?://[^\s，。；;）)】>\]\"']+")
OID_PATTERN = re.compile(r"1034:(\d{10,})")


class WeiboAPIError(RuntimeError):
    def __init__(self, code: Any, message: Any, reason: str):
        self.code = code
        self.message = message
        self.reason = reason
        super().__init__(f"Weibo component API error: {reason}. code={code} message={message}")


def _success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}


def _failure(exc: Exception, solution: str) -> dict[str, Any]:
    return download_runtime.failure_payload(exc, solution)


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _extract_first_url(value: str) -> Optional[str]:
    match = URL_PATTERN.search(html.unescape(value))
    return match.group(0) if match else None


def _normalize_protocol_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = html.unescape(value.strip())
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("http://"):
        return "https://" + value[len("http://") :]
    return value


def _extract_oid(value: str) -> str:
    normalized = unquote(html.unescape(value.strip()))
    match = OID_PATTERN.search(normalized)
    if match:
        return f"1034:{match.group(1)}"

    url = _extract_first_url(normalized)
    if url:
        match = OID_PATTERN.search(unquote(url))
        if match:
            return f"1034:{match.group(1)}"

    if normalized.isdigit() and len(normalized) >= 10:
        return f"1034:{normalized}"

    raise ValueError(
        "Unable to parse Weibo video OID. Use a weibo.com/tv/show/1034:<media_id> "
        "URL, h5.video.weibo.com/show URL, share text, or 1034:<media_id>."
    )


def _page_url(oid: str) -> str:
    return f"https://h5.video.weibo.com/show/{oid}"


def _component_headers(oid: str) -> dict[str, str]:
    page_path = f"/show/{oid}"
    return {
        "User-Agent": MOBILE_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded",
        "PAGE-REFERER": page_path,
        "Referer": _page_url(oid),
    }


def _fetch_play_info(oid: str) -> dict[str, Any]:
    component_payload = {COMPONENT_NAME: {"oid": oid}}
    body = (
        "data="
        + json.dumps(component_payload, ensure_ascii=False, separators=(",", ":"))
    ).encode("utf-8")
    request = Request(
        COMPONENT_API,
        data=body,
        headers=_component_headers(oid),
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if str(payload.get("code")) != "100000":
        raise WeiboAPIError(
            payload.get("code"),
            payload.get("msg"),
            "component API returned an error",
        )

    info = (payload.get("data") or {}).get(COMPONENT_NAME)
    if not isinstance(info, dict) or not info:
        raise WeiboAPIError(
            payload.get("code"),
            payload.get("msg"),
            "video is unavailable, private, deleted, or not a video object",
        )
    if info.get("object_type") not in (None, "video") or (
        not info.get("urls") and not info.get("stream_url")
    ):
        raise WeiboAPIError(
            payload.get("code"),
            payload.get("msg"),
            "component response contains no downloadable video URL",
        )
    return info


def _height_from_label_or_url(label: str, url: str) -> int:
    label_match = re.search(r"(\d{3,4})P", label, re.IGNORECASE)
    if label_match:
        return int(label_match.group(1))

    template_match = re.search(r"(?:template=|/)(\d{3,4})x(\d{3,4})", url)
    if template_match:
        return int(template_match.group(2))
    return 0


def _media_candidates(info: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    urls = info.get("urls") or {}
    if isinstance(urls, dict):
        for label, raw_url in urls.items():
            video_url = _normalize_protocol_url(raw_url)
            if not video_url or video_url in seen:
                continue
            seen.add(video_url)
            candidates.append(
                {
                    "label": str(label),
                    "height": _height_from_label_or_url(str(label), video_url),
                    "url": video_url,
                }
            )

    stream_url = _normalize_protocol_url(info.get("stream_url"))
    if stream_url and stream_url not in seen:
        candidates.append(
            {
                "label": "低清 360P",
                "height": _height_from_label_or_url("低清 360P", stream_url),
                "url": stream_url,
            }
        )

    return sorted(candidates, key=lambda item: item["height"], reverse=True)


def _quality_height(quality: str) -> Optional[int]:
    if quality == "best":
        return None
    return int(quality.removesuffix("p"))


def _choose_candidate(
    candidates: list[dict[str, Any]],
    quality: str = DEFAULT_QUALITY,
) -> dict[str, Any]:
    if quality not in QUALITY_CHOICES:
        raise ValueError(f"Unsupported quality {quality!r}; choose one of {QUALITY_CHOICES}.")
    if not candidates:
        raise RuntimeError("Weibo component response contains no media candidates.")

    requested_height = _quality_height(quality)
    if requested_height is None:
        return candidates[0]

    exact = next(
        (candidate for candidate in candidates if candidate["height"] == requested_height),
        None,
    )
    if exact:
        return exact

    lower = [
        candidate
        for candidate in candidates
        if 0 < candidate["height"] <= requested_height
    ]
    if lower:
        return max(lower, key=lambda item: item["height"])
    return min(candidates, key=lambda item: item["height"] or sys.maxsize)


def _clean_text(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return None
    return re.sub(r"<[^>]+>", "", html.unescape(value)).strip() or None


def _metadata(info: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = {
        "title": info.get("title"),
        "description": _clean_text(info.get("text")),
        "author": info.get("author") or info.get("nickname"),
        "author_id": info.get("author_id"),
        "cover_url": _normalize_protocol_url(info.get("cover_image")),
        "duration": info.get("duration_time"),
        "publish_time": info.get("real_date"),
        "video_orientation": info.get("video_orientation"),
        "statistics": {
            key: info.get(key)
            for key in (
                "play_count",
                "reposts_count",
                "comments_count",
                "attitudes_count",
            )
            if info.get(key) is not None
        },
        "available_qualities": [
            {"label": candidate["label"], "height": candidate["height"]}
            for candidate in candidates
        ],
    }
    return {
        key: value
        for key, value in metadata.items()
        if value not in (None, "", {}, [])
    }


def resolve_video_info(
    input_str: str,
    quality: str = DEFAULT_QUALITY,
) -> dict[str, Any]:
    oid = _extract_oid(input_str)
    info = _fetch_play_info(oid)
    candidates = _media_candidates(info)
    selected = _choose_candidate(candidates, quality=quality)
    return {
        "video_url": selected["url"],
        "platform": PLATFORM,
        "oid": oid,
        "media_id": info.get("media_id") or oid.split(":", 1)[1],
        "mid": info.get("mid"),
        "page_url": _page_url(oid),
        "quality": f"{selected['height']}p" if selected["height"] else selected["label"],
        "quality_label": selected["label"],
        "metadata": _metadata(info, candidates),
    }


def resolve_video_url(input_str: str, quality: str = DEFAULT_QUALITY) -> str:
    return resolve_video_info(input_str, quality=quality)["video_url"]


def _resolve_output_dir(output_dir: Optional[PathLikeStr] = None) -> Path:
    configured = str(output_dir) if output_dir is not None else None
    return download_runtime.resolve_output_directory(configured).path


def _safe_name(value: Any) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    return cleaned or "video"


def _download_headers(referer: str) -> dict[str, str]:
    return {
        "User-Agent": DESKTOP_USER_AGENT,
        "Accept": "*/*",
        "Referer": referer,
    }


def _download_file(video_url: str, output_path: Path, referer: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=str(output_path.parent),
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        request = Request(video_url, headers=_download_headers(referer))
        with urlopen(request, timeout=60) as response, temporary_path.open("wb") as output:
            prefix = response.read(32)
            content_type = response.headers.get("Content-Type", "")
            if "video/" not in content_type.lower() and b"ftyp" not in prefix:
                raise RuntimeError(
                    f"Weibo CDN response is not MP4. content_type={content_type!r}"
                )
            output.write(prefix)
            shutil.copyfileobj(response, output, length=1024 * 1024)

        if temporary_path.stat().st_size == 0:
            raise RuntimeError("Downloaded Weibo video is empty.")
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return output_path


def _output_path(info: dict[str, Any], output_dir: Path) -> Path:
    media_id = _safe_name(info.get("media_id") or info["oid"])
    quality = _safe_name(info.get("quality") or DEFAULT_QUALITY)
    return output_dir / f"weibo_{media_id}_{quality}.mp4"


def download_with_info(
    input_str: str,
    output_dir: Optional[PathLikeStr] = None,
    quality: str = DEFAULT_QUALITY,
) -> dict[str, Any]:
    configured_output_dir = str(output_dir) if output_dir is not None else None
    output_decision = download_runtime.resolve_output_directory(configured_output_dir)
    resolved_output_dir = output_decision.path
    info = resolve_video_info(input_str, quality=quality)
    output_path = _output_path(info, resolved_output_dir)
    try:
        saved_path = _download_file(
            info["video_url"],
            output_path,
            referer=info["page_url"],
        )
    except HTTPError as exc:
        if exc.code not in REFRESHABLE_DOWNLOAD_STATUS:
            raise
        info = resolve_video_info(input_str, quality=quality)
        output_path = _output_path(info, resolved_output_dir)
        saved_path = _download_file(
            info["video_url"],
            output_path,
            referer=info["page_url"],
        )
        info["download_retry_reason"] = f"refreshed temporary URL after HTTP {exc.code}"

    absolute_path = saved_path.resolve()
    if not absolute_path.exists() or absolute_path.stat().st_size == 0:
        raise FileNotFoundError(f"Downloaded file not found or empty: {absolute_path}")
    return {
        "file_path": str(absolute_path),
        "output_directory": output_decision.to_dict(),
        **info,
    }


def download(
    input_str: str,
    output_dir: Optional[PathLikeStr] = None,
    quality: str = DEFAULT_QUALITY,
) -> str:
    return download_with_info(
        input_str,
        output_dir=output_dir,
        quality=quality,
    )["file_path"]


def check_environment() -> dict[str, Any]:
    return {
        "mobile_component_api": True,
        "login_required": False,
        "external_dependencies": [],
        "supports_share_text": True,
        "supports_oid": True,
        "default_quality": DEFAULT_QUALITY,
        "quality_choices": list(QUALITY_CHOICES),
        "temporary_url_refresh_on_http": sorted(REFRESHABLE_DOWNLOAD_STATUS),
        "missing": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve or download a public Weibo video through the mobile H5 component API."
    )
    parser.add_argument(
        "url_or_oid",
        help="Weibo video URL, H5 video URL, share text, or 1034:<media_id> OID.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for downloaded files. Defaults to ./downloads.",
    )
    parser.add_argument(
        "--quality",
        choices=QUALITY_CHOICES,
        default=DEFAULT_QUALITY,
        help="Requested quality. Defaults to 480p.",
    )
    parser.add_argument(
        "--print-url",
        action="store_true",
        help="Print the freshly resolved MP4 URL instead of downloading it.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    parser.add_argument("--check", action="store_true", help="Check capabilities and exit.")
    args = parser.parse_args()

    try:
        if args.check:
            payload = _success(check_environment())
        elif args.print_url:
            payload = _success(
                resolve_video_info(args.url_or_oid, quality=args.quality)
            )
        else:
            payload = _success(
                download_with_info(
                    args.url_or_oid,
                    output_dir=args.output_dir,
                    quality=args.quality,
                )
            )

        if args.json or args.check or args.print_url:
            _print_json(payload)
        else:
            print(payload["data"]["file_path"])
        return 0
    except Exception as exc:
        payload = _failure(
            exc,
            "Use a public weibo.com/tv/show/1034:<media_id> link, H5 video link, "
            "share text, or OID. Temporary CDN URLs expire; rerun the same command "
            "to refresh them. Private, deleted, non-video, or restricted posts are unsupported.",
        )
        if isinstance(exc, WeiboAPIError):
            payload["data"] = {
                "code": exc.code,
                "message": exc.message,
                "reason": exc.reason,
            }
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
