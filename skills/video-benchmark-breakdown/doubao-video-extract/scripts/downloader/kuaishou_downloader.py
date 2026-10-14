#!/usr/bin/env python3
"""Download a Kuaishou video by page URL, short link/share text, photo ID, or MP4 URL.

Usage:
  python3 scripts/downloader/kuaishou_downloader.py <url_or_id>
  python3 scripts/downloader/kuaishou_downloader.py <url_or_id> --output-dir /path/to/project/downloads
  python3 scripts/downloader/kuaishou_downloader.py <url_or_id> --print-url

Output:
  Prints the absolute file path on success, or the resolved MP4 URL with --print-url.
"""

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
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "util"))

from script_utils import (
    USER_AGENT,
    ensure_writable_dir,
    extract_first_url,
    failure,
    normalize_share_input,
    print_json,
    success,
)


PathLikeStr = Union[str, os.PathLike[str]]

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.0 Mobile/15E148 Safari/604.1"
)
MOBILE_H5_HOST = "v.m.chenzhongtech.com"
KUAISHOU_CDN_MARKERS = ("kwaicdn", "oskwai", "kwimgs")


def _resolve_output_dir(output_dir: Optional[PathLikeStr] = None) -> Path:
    configured_dir = output_dir or os.environ.get("VIDEO_SUBTITLE_DOWNLOAD_DIR")
    if configured_dir:
        return ensure_writable_dir(Path(configured_dir), fallback_name="downloads")

    return ensure_writable_dir(Path.cwd() / "downloads", fallback_name="downloads")


def _normalize_input(input_str: str) -> str:
    input_str = extract_first_url(input_str) or normalize_share_input(input_str)
    parsed = urlparse(input_str)
    if parsed.scheme and parsed.netloc:
        return input_str

    return _to_mobile_h5_url(input_str)


def _to_mobile_h5_url(input_str: str) -> str:
    parsed = urlparse(input_str)
    if _is_mp4_url(input_str):
        return input_str

    if not parsed.scheme:
        photo_id = _safe_name(input_str)
        return f"https://{MOBILE_H5_HOST}/fw/photo/{photo_id}"

    host = parsed.netloc.lower()
    if host == MOBILE_H5_HOST or parsed.path.startswith("/fw/photo/"):
        return input_str

    photo_id = _extract_photo_id(input_str)
    if photo_id != "video" and ("kuaishou.com" in host or "chenzhongtech.com" in host):
        return f"https://{MOBILE_H5_HOST}/fw/photo/{photo_id}"

    return input_str


def _extract_photo_id(input_str: str) -> str:
    parsed = urlparse(input_str)
    match = re.search(r"/short-video/([^/?#]+)", parsed.path)
    if match:
        return _safe_name(unquote(match.group(1)))

    match = re.search(r"/fw/photo/([^/?#]+)", parsed.path)
    if match:
        return _safe_name(unquote(match.group(1)))

    query = parse_qs(parsed.query)
    photo_id = query.get("photoId", [""])[0]
    if photo_id:
        return _safe_name(photo_id)

    cache_key = query.get("clientCacheKey", [""])[0]
    if cache_key:
        return _safe_name(cache_key.split("_", 1)[0])

    if not parsed.scheme and input_str:
        return _safe_name(input_str)

    return "video"


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return value or "video"


def _is_mp4_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.path.lower().endswith(".mp4")


def _request_headers(referer: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Accept": "*/*",
        "User-Agent": USER_AGENT,
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _mobile_page_headers(referer: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "User-Agent": MOBILE_USER_AGENT,
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _fetch_text(url: str) -> str:
    page_html, _ = _fetch_mobile_page(url)
    return page_html


def _fetch_mobile_page(url: str) -> tuple[str, str]:
    req = Request(url, headers=_mobile_page_headers("https://www.kuaishou.com/"))
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", "ignore"), response.geturl()


def _safe_fetch_mobile_page(url: str) -> tuple[Optional[str], str, Optional[str]]:
    try:
        page_html, final_url = _fetch_mobile_page(url)
        return page_html, final_url, None
    except Exception as exc:
        return None, url, str(exc)


def _extract_mp4_candidates_from_html(page_html: str) -> list[str]:
    patterns = [
        r'https?:\\?/\\?/[^"\'<>]+?\.mp4[^"\'<>]*',
        r'https?://[^"\'<>\\]+?\.mp4[^"\'<>\\]*',
        r'https?%3A%2F%2F[^"\'<>]+?\.mp4[^"\'<>]*',
    ]
    candidates = []
    for pattern in patterns:
        for match in re.finditer(pattern, page_html):
            candidate = html.unescape(unquote(match.group(0))).replace("\\/", "/")
            if any(marker in candidate for marker in KUAISHOU_CDN_MARKERS) and candidate not in candidates:
                candidates.append(candidate)

    return candidates


def _mp4_quality_score(video_url: str) -> tuple[int, int]:
    parsed = urlparse(video_url)
    query = parse_qs(parsed.query)
    quality = query.get("tt", [""])[0]
    if quality == "hd15":
        quality_score = 3
    elif quality == "b":
        quality_score = 2
    else:
        quality_score = 1

    host_score = 2 if ("kwaicdn" in parsed.netloc or "oskwai" in parsed.netloc) else 1
    return quality_score, host_score


def _validate_mp4_url(video_url: str, referer: Optional[str] = None) -> bool:
    headers = _request_headers(referer)
    headers["Range"] = "bytes=0-15"
    try:
        req = Request(video_url, headers=headers)
        with urlopen(req, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            prefix = response.read(16)
        return "video" in content_type.lower() or b"ftyp" in prefix
    except Exception:
        return False


def _choose_best_mp4(candidates: list[str], referer: Optional[str] = None, validate: bool = True) -> Optional[str]:
    for candidate in sorted(candidates, key=_mp4_quality_score, reverse=True):
        if not validate or _validate_mp4_url(candidate, referer=referer):
            return candidate
    return None


def _candidate_debug(candidates: list[str], referer: Optional[str] = None) -> list[dict[str, Any]]:
    debug = []
    for candidate in sorted(candidates, key=_mp4_quality_score, reverse=True):
        debug.append(
            {
                "url": candidate,
                "quality_score": _mp4_quality_score(candidate),
                "validated": _validate_mp4_url(candidate, referer=referer),
            }
        )
    return debug


def _extract_mp4_from_html(page_html: str) -> Optional[str]:
    return _choose_best_mp4(_extract_mp4_candidates_from_html(page_html), validate=False)


def _extract_html_metadata(page_html: str) -> dict[str, Any]:
    def meta_value(*names: str) -> Optional[str]:
        for name in names:
            patterns = [
                rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
                rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
            ]
            for pattern in patterns:
                match = re.search(pattern, page_html, re.IGNORECASE)
                if match:
                    return html.unescape(match.group(1)).strip()
        return None

    title_match = re.search(r"<title[^>]*>(.*?)</title>", page_html, re.IGNORECASE | re.DOTALL)
    title = html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else None
    return {
        key: value
        for key, value in {
            "title": meta_value("og:title", "twitter:title") or title,
            "description": meta_value("og:description", "description"),
            "cover_url": meta_value("og:image", "twitter:image"),
        }.items()
        if value not in (None, "", {}, [])
    }


def resolve_video_url(input_str: str) -> str:
    return resolve_video_info(input_str)["video_url"]


def resolve_video_info(input_str: str) -> dict[str, Any]:
    original_url = _normalize_input(input_str)
    if _is_mp4_url(original_url):
        photo_id = _extract_photo_id(original_url)
        return {"video_url": original_url, "page_url": original_url, "photo_id": photo_id, "platform": "kuaishou", "metadata": {}}

    page_url = _to_mobile_h5_url(original_url)
    page_html, final_page_url, fetch_error = _safe_fetch_mobile_page(page_url)
    if page_html is None:
        raise RuntimeError(
            "Unable to fetch the Kuaishou mobile H5 page. "
            f"page_url={page_url} error={fetch_error}"
        )
    page_url = final_page_url or page_url
    photo_id = _extract_photo_id(page_url)
    candidates = _extract_mp4_candidates_from_html(page_html)
    video_url = _choose_best_mp4(candidates, referer=page_url)
    if video_url:
        metadata = _extract_html_metadata(page_html)
        if candidates:
            metadata["mp4_candidates"] = candidates
        return {
            "video_url": video_url,
            "page_url": page_url,
            "photo_id": photo_id,
            "platform": "kuaishou",
            "metadata": metadata,
        }

    raise RuntimeError(
        "Unable to resolve a direct MP4 URL from the Kuaishou mobile H5 page. "
        "The work may be private, deleted, image-only, or the page structure may have changed. "
        f"debug={json.dumps({'page_url': page_url, 'candidate_count': len(candidates), 'candidates': _candidate_debug(candidates, referer=page_url)}, ensure_ascii=False)}"
    )


def _download_file(video_url: str, output_path: Path, referer: Optional[str] = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=str(output_path.parent),
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    try:
        req = Request(video_url, headers=_request_headers(referer))
        with urlopen(req, timeout=60) as response, tmp_path.open("wb") as out_file:
            shutil.copyfileobj(response, out_file, length=1024 * 1024)
        tmp_path.replace(output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return output_path


def download(input_str: str, output_dir: Optional[PathLikeStr] = None) -> str:
    page_url = _normalize_input(input_str)
    photo_id = _extract_photo_id(page_url)
    out_dir = _resolve_output_dir(output_dir)

    info = resolve_video_info(page_url)
    video_url = info["video_url"]
    page_url = info.get("page_url", page_url)
    photo_id = info.get("photo_id") or photo_id
    output_path = out_dir / f"kuaishou_{photo_id}.mp4"
    saved_path = _download_file(video_url, output_path, referer=page_url)

    abs_path = saved_path.resolve()
    if not abs_path.exists():
        raise FileNotFoundError(f"Downloaded file not found: {abs_path}")

    return str(abs_path)


def check_environment() -> dict[str, object]:
    return {
        "mobile_h5_download": True,
        "direct_mp4_fallback": True,
        "supports_share_text": True,
        "supports_short_links": True,
        "missing": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a Kuaishou video by page URL, photo ID, or resolved MP4 URL."
    )
    parser.add_argument("url_or_id", help="Kuaishou page URL, photo ID, or resolved MP4 URL")
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory for downloaded files. Defaults to $VIDEO_SUBTITLE_DOWNLOAD_DIR "
            "or ./downloads under the current working directory."
        ),
    )
    parser.add_argument(
        "--print-url",
        action="store_true",
        help="Print the resolved MP4 URL instead of downloading it.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    parser.add_argument("--check", action="store_true", help="Check dependencies and exit.")
    args = parser.parse_args()

    input_str = args.url_or_id.strip()

    try:
        if args.check:
            print_json(success(check_environment()))
            return 0
        if args.print_url:
            info = resolve_video_info(input_str)
            if args.json:
                print_json(success(info))
            else:
                print(info["video_url"])
        else:
            file_path = download(input_str, output_dir=args.output_dir)
            if args.json:
                try:
                    info = resolve_video_info(input_str)
                except Exception:
                    info = {"platform": "kuaishou", "metadata": {}}
                print_json(success({"file_path": file_path, **{k: v for k, v in info.items() if k != "video_url"}}))
            else:
                print(file_path)
    except Exception as exc:
        payload = failure(
            exc,
            "Try --print-url --json for structured resolver debug, verify the work is public video content, "
            "or continue with a local MP4 through `social_video_to_minutes.py --media-mode video`.",
        )
        if args.json:
            print_json(payload)
        else:
            print(f"Download failed: {payload['error']}\nNext step: {payload['solution']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
