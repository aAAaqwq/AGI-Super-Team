#!/usr/bin/env python3
"""Download a Bilibili video with public player APIs and browser-like headers."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional, Union
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "util"))

from script_utils import (  # noqa: E402
    USER_AGENT,
    ensure_writable_dir,
    failure,
    normalize_share_input,
    print_json,
    resolve_short_video_url,
    success,
)


PathLikeStr = Union[str, os.PathLike[str]]

QUALITY_LABELS = {
    16: "360P",
    32: "480P",
    64: "720P",
    80: "1080P",
}

BILIBILI_SHARE_PARAM_KEYS = {
    "-Arouter",
    "buvid",
    "mid",
    "timestamp",
    "share_session_id",
    "share_from",
    "share_medium",
    "share_plat",
    "share_source",
    "up_id",
}

RETRYABLE_HTTP_STATUS = {403, 412, 429}
API_RETRY_DELAYS = (1, 3, 6)
DOWNLOAD_RETRY_DELAYS: tuple[int, ...] = ()
HUMAN_VERIFICATION_MARKERS = ("出错啦", "验证码", "人机验证", "安全验证", "Precondition Failed")


class BilibiliHTTPError(RuntimeError):
    def __init__(self, status: int, reason: str, url: str, category: str = "http_error"):
        self.status = status
        self.reason = reason
        self.url = url
        self.category = category
        super().__init__(f"Bilibili HTTP {status}: {reason}. url={url}")


class BilibiliAPIError(RuntimeError):
    def __init__(self, code: Any, message: Any, reason: str):
        self.code = code
        self.message = message
        self.reason = reason
        super().__init__(f"Bilibili API error: {reason}. code={code} message={message}")


def _headers(referer: str = "https://www.bilibili.com/") -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Referer": referer,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def _classify_http_status(status: int) -> str:
    if status in {412, 429}:
        return "platform temporary risk control or rate limit; retry after a short wait"
    if status == 403:
        return "forbidden, expired CDN URL, or login-only resource"
    if status == 404:
        return "video or resource not found"
    return "HTTP request failed"


def _classify_http_category(status: int, body: str = "") -> str:
    if status == 412 and _looks_like_human_verification(body):
        return "human_verification_required"
    if status in {412, 429}:
        return "temporary_rate_limit"
    if status == 403:
        return "cdn_forbidden_or_expired"
    if status == 404:
        return "not_found"
    return "http_error"


def _looks_like_human_verification(body: str) -> bool:
    return any(marker in body for marker in HUMAN_VERIFICATION_MARKERS)


def _read_http_error_body(exc: HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", "ignore")
    except Exception:
        return ""


class _BytesResponse:
    def __init__(self, content: bytes, headers: Optional[dict[str, str]] = None):
        self._content = content
        self.headers = headers or {}
        self._offset = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = len(self._content) - self._offset
        chunk = self._content[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _curl_cffi_get(url: str, headers: dict[str, str], timeout: int):
    try:
        curl_requests = importlib.import_module("curl_cffi.requests")
    except Exception as exc:
        raise RuntimeError("optional_tls_impersonation_unavailable: curl_cffi is not installed") from exc

    session = curl_requests.Session(impersonate="chrome120")
    response = session.get(url, headers=headers, timeout=timeout)
    status_code = getattr(response, "status_code", 200)
    content = getattr(response, "content", b"")
    if isinstance(content, str):
        content = content.encode("utf-8")
    if status_code >= 400:
        body = content.decode("utf-8", "ignore")
        raise BilibiliHTTPError(
            status_code,
            _classify_http_status(status_code),
            url,
            category=_classify_http_category(status_code, body),
        )
    return _BytesResponse(content, dict(getattr(response, "headers", {}) or {}))


def _open_with_tls_fallback(req: Request, timeout: int):
    headers = dict(req.header_items())
    return _curl_cffi_get(req.full_url, headers=headers, timeout=timeout)


def _open_with_retries(req: Request, timeout: int, delays: tuple[int, ...]):
    attempts = len(delays) + 1
    for attempt in range(attempts):
        try:
            return urlopen(req, timeout=timeout)
        except HTTPError as exc:
            status = exc.code
            body = _read_http_error_body(exc)
            category = _classify_http_category(status, body)
            if category == "human_verification_required":
                try:
                    return _open_with_tls_fallback(req, timeout=timeout)
                except RuntimeError as fallback_exc:
                    raise BilibiliHTTPError(
                        status,
                        f"human_verification_required; {fallback_exc}",
                        req.full_url,
                        category=category,
                    ) from exc
            if status not in RETRYABLE_HTTP_STATUS or attempt >= len(delays):
                raise BilibiliHTTPError(
                    status,
                    _classify_http_status(status),
                    req.full_url,
                    category=category,
                ) from exc
            time.sleep(delays[attempt])


def _fetch_json(url: str, referer: str = "https://www.bilibili.com/") -> dict[str, Any]:
    req = Request(url, headers=_headers(referer))
    with _open_with_retries(req, timeout=30, delays=API_RETRY_DELAYS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 0:
        code = payload.get("code")
        message = payload.get("message")
        if code in {-404, 62002}:
            reason = "video not found or unavailable"
        elif code in {-101, -10403}:
            reason = "login or permission required"
        elif code in {-352, -412}:
            reason = "platform temporary risk control or rate limit; retry later"
        else:
            reason = "API returned an error"
        raise BilibiliAPIError(code, message, reason)
    return payload


def _resolve_output_dir(output_dir: Optional[PathLikeStr] = None) -> Path:
    configured_dir = output_dir or os.environ.get("VIDEO_EXTRACT_DOWNLOAD_DIR") or os.environ.get(
        "VIDEO_SUBTITLE_DOWNLOAD_DIR"
    )
    if configured_dir:
        return ensure_writable_dir(Path(configured_dir), fallback_name="downloads")
    return ensure_writable_dir(Path.cwd() / "downloads", fallback_name="downloads")


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return value or "video"


def _extract_bilibili_share_params(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    params: dict[str, str] = {}
    for key in BILIBILI_SHARE_PARAM_KEYS:
        values = query.get(key)
        if values:
            params[key] = values[0]
    return params


def _bilibili_referer(value: str, canonical_url: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc and parsed.query:
        return value
    return canonical_url


def _parse_bilibili_input(input_str: str) -> dict[str, Any]:
    value = resolve_short_video_url(normalize_share_input(input_str))
    parsed = urlparse(value)
    path = parsed.path if parsed.scheme else value
    share_params = _extract_bilibili_share_params(value)

    bvid_match = re.search(r"(BV[0-9A-Za-z]{10})", path)
    if bvid_match:
        bvid = bvid_match.group(1)
        canonical_url = f"https://www.bilibili.com/video/{bvid}/"
        return {
            "bvid": bvid,
            "referer": _bilibili_referer(value, canonical_url),
            "share_params": share_params,
        }

    av_match = re.search(r"(?:^|/)(?:av)?(\d+)(?:/|$)", path, re.IGNORECASE)
    if av_match:
        aid = av_match.group(1)
        canonical_url = f"https://www.bilibili.com/video/av{aid}/"
        return {
            "aid": aid,
            "referer": _bilibili_referer(value, canonical_url),
            "share_params": share_params,
        }

    raise ValueError("Unable to parse Bilibili BV ID or av ID from input.")


def _pagelist_id_params(video: dict[str, Any]) -> dict[str, str]:
    if video.get("aid"):
        return {"aid": str(video["aid"])}
    return {"bvid": str(video["bvid"])}


def _playurl_id_params(video: dict[str, Any]) -> dict[str, str]:
    if video.get("aid"):
        return {"avid": str(video["aid"])}
    return {"bvid": str(video["bvid"])}


def _view_id_params(video: dict[str, Any]) -> dict[str, str]:
    if video.get("aid"):
        return {"aid": str(video["aid"])}
    return {"bvid": str(video["bvid"])}


def _extract_view_metadata(view_data: dict[str, Any]) -> dict[str, Any]:
    owner = view_data.get("owner") if isinstance(view_data.get("owner"), dict) else {}
    stat = view_data.get("stat") if isinstance(view_data.get("stat"), dict) else {}
    return {
        key: value
        for key, value in {
            "title": view_data.get("title"),
            "description": view_data.get("desc"),
            "bvid": view_data.get("bvid"),
            "aid": view_data.get("aid"),
            "cover_url": view_data.get("pic"),
            "duration": view_data.get("duration"),
            "pubdate": view_data.get("pubdate"),
            "owner_name": owner.get("name"),
            "owner_mid": owner.get("mid"),
            "stat": stat or None,
        }.items()
        if value not in (None, "", {}, [])
    }


def _fetch_view_detail(video: dict[str, Any]) -> dict[str, Any]:
    url = "https://api.bilibili.com/x/web-interface/view/detail?" + urlencode(_view_id_params(video))
    payload = _fetch_json(url, referer=video["referer"])
    view_data = payload.get("data", {}).get("View") or {}
    if not isinstance(view_data, dict) or not view_data:
        raise RuntimeError("Bilibili view/detail returned no View data.")
    return view_data


def _pages_from_view_detail(view_data: dict[str, Any]) -> list[dict[str, Any]]:
    pages = view_data.get("pages")
    if isinstance(pages, list) and pages:
        return pages
    cid = view_data.get("cid")
    if cid:
        return [{"cid": cid, "page": 1, "part": view_data.get("title") or ""}]
    raise RuntimeError("Bilibili view/detail returned no pages or cid.")


def get_video_metadata(input_str: str) -> dict[str, Any]:
    video = _parse_bilibili_input(input_str)
    url = "https://api.bilibili.com/x/web-interface/view?" + urlencode(_view_id_params(video))
    try:
        payload = _fetch_json(url, referer=video["referer"])
        data = payload.get("data") or {}
    except BilibiliAPIError as exc:
        if exc.code not in {-404, 62002}:
            raise
        data = _fetch_view_detail(video)
    if not isinstance(data, dict):
        return {}
    return _extract_view_metadata(data)


def _safe_video_metadata(input_str: str) -> dict[str, Any]:
    try:
        return get_video_metadata(input_str)
    except Exception:
        return {}


def get_pagelist(input_str: str) -> dict[str, Any]:
    video = _parse_bilibili_input(input_str)
    url = "https://api.bilibili.com/x/player/pagelist?" + urlencode(_pagelist_id_params(video))
    try:
        payload = _fetch_json(url, referer=video["referer"])
        pages = payload.get("data") or []
    except BilibiliAPIError as exc:
        if exc.code not in {-404, 62002}:
            raise
        view_data = _fetch_view_detail(video)
        video = {
            **video,
            "aid": view_data.get("aid") or video.get("aid"),
            "bvid": view_data.get("bvid") or video.get("bvid"),
            "story_detail_fallback_used": True,
        }
        pages = _pages_from_view_detail(view_data)
    if not pages:
        view_data = _fetch_view_detail(video)
        video = {
            **video,
            "aid": view_data.get("aid") or video.get("aid"),
            "bvid": view_data.get("bvid") or video.get("bvid"),
            "story_detail_fallback_used": True,
        }
        pages = _pages_from_view_detail(view_data)
    return {"video": video, "pages": pages}


def get_playurl(input_str: str, cid: Optional[int] = None, page: int = 1, quality: int = 32) -> dict[str, Any]:
    if quality > 32:
        raise ValueError("Bilibili unauthenticated quality limit: use --quality 32 or --quality 16.")
    pagelist = get_pagelist(input_str)
    pages = pagelist["pages"]
    if cid is None:
        if page < 1 or page > len(pages):
            raise ValueError(f"Invalid page {page}; available pages: 1-{len(pages)}")
        cid = int(pages[page - 1]["cid"])

    video = pagelist["video"]
    params = {
        **_playurl_id_params(video),
        "cid": str(cid),
        "qn": str(quality),
        "fnval": "0",
        **video.get("share_params", {}),
    }
    url = "https://api.bilibili.com/x/player/playurl?" + urlencode(params)
    payload = _fetch_json(url, referer=video["referer"])
    durl = payload.get("data", {}).get("durl") or []
    if not durl:
        raise RuntimeError(
            "Bilibili playurl returned no downloadable durl. "
            "This is usually an unauthenticated quality limit; retry with --quality 32 or --quality 16."
        )
    return {
        "video": video,
        "cid": cid,
        "page": page,
        "quality": quality,
        "quality_label": QUALITY_LABELS.get(quality, str(quality)),
        "url": durl[0]["url"],
        "metadata": _safe_video_metadata(input_str),
        "pages": pages,
        "playurl": payload,
    }


def get_playurl_with_fallback(
    input_str: str,
    cid: Optional[int] = None,
    page: int = 1,
    quality: int = 32,
) -> dict[str, Any]:
    qualities = [quality]
    if quality == 32:
        qualities.append(16)

    errors = []
    for qn in qualities:
        try:
            play = get_playurl(input_str, cid=cid, page=page, quality=qn)
            if errors:
                play["fallback_errors"] = errors
            return play
        except Exception as exc:
            errors.append({"quality": qn, "error": str(exc)})

    raise RuntimeError(
        "Bilibili playurl failed for all unauthenticated qualities. "
        f"errors={json.dumps(errors, ensure_ascii=False)}"
    )


def _download_play(play: dict[str, Any], output_dir: Optional[PathLikeStr] = None) -> str:
    out_dir = _resolve_output_dir(output_dir)
    video = play["video"]
    video_id = video.get("bvid") or f"av{video['aid']}"
    output_path = out_dir / f"bilibili_{_safe_name(str(video_id))}_p{play['page']}_{play['quality_label']}.mp4"

    req = Request(play["url"], headers=_headers(video["referer"]))
    with _open_with_retries(req, timeout=60, delays=DOWNLOAD_RETRY_DELAYS) as response, output_path.open("wb") as out_file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out_file.write(chunk)

    abs_path = output_path.resolve()
    if not abs_path.exists() or abs_path.stat().st_size == 0:
        raise FileNotFoundError(f"Downloaded file not found or empty: {abs_path}")
    return str(abs_path)


def download(
    input_str: str,
    output_dir: Optional[PathLikeStr] = None,
    cid: Optional[int] = None,
    page: int = 1,
    quality: int = 32,
) -> str:
    play = get_playurl_with_fallback(input_str, cid=cid, page=page, quality=quality)
    try:
        return _download_play(play, output_dir=output_dir)
    except BilibiliHTTPError as exc:
        if exc.status not in RETRYABLE_HTTP_STATUS:
            raise
        refreshed_play = get_playurl_with_fallback(input_str, cid=cid, page=page, quality=play["quality"])
        refreshed_play["download_retry_reason"] = str(exc)
        return _download_play(refreshed_play, output_dir=output_dir)


def check_environment() -> dict[str, object]:
    try:
        importlib.import_module("curl_cffi.requests")
        curl_cffi_available = True
    except Exception:
        curl_cffi_available = False
    return {
        "api_download": True,
        "login_required": False,
        "default_quality": 32,
        "quality_labels": QUALITY_LABELS,
        "supports_bvid": True,
        "supports_aid": True,
        "supports_cid": True,
        "supports_share_text": True,
        "supports_short_links": True,
        "quality_fallback": [32, 16],
        "story_detail_fallback": True,
        "optional_tls_impersonation": {
            "available": curl_cffi_available,
            "provider": "curl_cffi",
            "used_only_after_human_verification_412": True,
        },
        "http_retries": {
            "api_statuses": sorted(RETRYABLE_HTTP_STATUS),
            "download_statuses": sorted(RETRYABLE_HTTP_STATUS),
            "download_refreshes_playurl_once": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a Bilibili video through public player APIs.")
    parser.add_argument("url_or_id", help="Bilibili share text, URL, b23.tv short link, BV ID, av ID, or aid number")
    parser.add_argument("--output-dir", help="Directory for downloaded files. Defaults to ./downloads.")
    parser.add_argument("--cid", type=int, help="Bilibili cid. Defaults to the selected page cid.")
    parser.add_argument("--page", type=int, default=1, help="Page index for multi-P videos. Defaults to 1.")
    parser.add_argument(
        "--quality",
        type=int,
        choices=sorted(QUALITY_LABELS),
        default=32,
        help="Quality code. Unauthenticated flow should use 16 or 32. Defaults to 32.",
    )
    parser.add_argument("--print-url", action="store_true", help="Print resolved video URL instead of downloading.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    parser.add_argument("--check", action="store_true", help="Check downloader capabilities and exit.")
    args = parser.parse_args()

    try:
        if args.check:
            payload = success(check_environment())
        elif args.print_url:
            play = get_playurl_with_fallback(args.url_or_id, cid=args.cid, page=args.page, quality=args.quality)
            payload = success(
                {
                    "url": play["url"],
                    "video_url": play["url"],
                    "platform": "bilibili",
                    "cid": play["cid"],
                    "quality": play["quality"],
                    "quality_label": play["quality_label"],
                    "metadata": play["metadata"],
                    "pages": play["pages"],
                    "fallback_errors": play.get("fallback_errors", []),
                }
            )
        else:
            play = get_playurl_with_fallback(args.url_or_id, cid=args.cid, page=args.page, quality=args.quality)
            file_path = _download_play(play, output_dir=args.output_dir)
            payload = success(
                {
                    "file_path": file_path,
                    "platform": "bilibili",
                    "video_url": play["url"],
                    "cid": play["cid"],
                    "quality": play["quality"],
                    "quality_label": play["quality_label"],
                    "metadata": play["metadata"],
                    "pages": play["pages"],
                    "fallback_errors": play.get("fallback_errors", []),
                }
            )

        if args.json or args.check or args.print_url:
            print_json(payload)
        else:
            print(payload["data"]["file_path"])
    except Exception as exc:
        payload = failure(
            exc,
            "Use Bilibili share text, b23.tv short link, BV/av URL or ID. For temporary risk control, retry "
            "the same CLI after a short wait; for quality limits, keep --quality at 32 or 16; for CDN 403, "
            "the downloader refreshes playurl once automatically.",
        )
        if isinstance(exc, BilibiliHTTPError):
            payload["data"] = {
                "status": exc.status,
                "category": exc.category,
                "reason": exc.reason,
                "url": exc.url,
            }
        elif isinstance(exc, BilibiliAPIError):
            payload["data"] = {
                "code": exc.code,
                "message": exc.message,
                "reason": exc.reason,
            }
        if args.json:
            print_json(payload)
        else:
            print(f"Download failed: {payload['error']}\nNext step: {payload['solution']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
