#!/usr/bin/env python3
"""Generate one MuAPI FLUX 3 video with a single, confirmed POST."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable


API_BASE = "https://api.muapi.ai/api/v1"
ENDPOINT = "flux-3-text-to-video"
TERMINAL_SUCCESS = {"completed", "complete", "succeeded", "success", "done"}
TERMINAL_FAILURE = {"failed", "failure", "error", "canceled", "cancelled", "timeout"}
TRANSIENT_HTTP_CODES = {408, 429, 500, 502, 503, 504}
ASPECT_RATIOS = ("21:9", "2:1", "16:9", "4:3", "1:1", "3:4", "9:16")
RESOLUTIONS = ("720p", "1080p")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_VIDEO_BYTES = 512 * 1024 * 1024


class MuapiVideoError(RuntimeError):
    """Raised when a MuAPI request cannot be completed safely."""


def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _redact(value: str, api_key: str) -> str:
    if api_key:
        value = value.replace(api_key, "[redacted]")
    return value[:500]


def _request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    *,
    attempts: int = 1,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "agi-super-team-muapi-video-gen/1.0",
        },
    )

    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                decoded_bytes = response.read(MAX_JSON_BYTES + 1)
                if len(decoded_bytes) > MAX_JSON_BYTES:
                    raise MuapiVideoError("MuAPI returned an oversized JSON response")
                result = json.loads(decoded_bytes.decode("utf-8"))
                if not isinstance(result, dict):
                    raise MuapiVideoError("MuAPI returned a non-object response")
                return result
        except urllib.error.HTTPError as exc:
            detail = exc.read(MAX_JSON_BYTES).decode("utf-8", errors="replace")
            if exc.code in TRANSIENT_HTTP_CODES and attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise MuapiVideoError(
                f"MuAPI {method} failed with HTTP {exc.code}: {_redact(detail, api_key)}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise MuapiVideoError(f"MuAPI {method} request failed: {_redact(str(exc), api_key)}") from exc
        except json.JSONDecodeError as exc:
            raise MuapiVideoError("MuAPI returned invalid JSON") from exc

    raise MuapiVideoError(f"MuAPI {method} request exhausted its attempts")


def _prediction_id(response: dict[str, Any]) -> str:
    data = _unwrap(response)
    request_id = data.get("request_id") or data.get("id") or data.get("prediction_id")
    if not request_id:
        raise MuapiVideoError(
            "MuAPI returned no identifiable prediction; do not resubmit automatically"
        )
    return str(request_id)


def submit_prediction(api_key: str, payload: dict[str, Any]) -> str:
    """Submit exactly once; generation POSTs are intentionally not retried."""

    response = _request_json(
        "POST", f"{API_BASE}/{ENDPOINT}", api_key, payload, attempts=1
    )
    return _prediction_id(response)


def _output_urls(value: Any) -> list[str]:
    if isinstance(value, str):
        parsed = urllib.parse.urlparse(value)
        return [value] if parsed.scheme in {"http", "https"} and parsed.netloc else []
    if isinstance(value, dict):
        urls: list[str] = []
        for key in ("outputs", "output", "video_url", "url", "result", "data"):
            if key in value:
                urls.extend(_output_urls(value[key]))
        if urls:
            return urls
        for item in value.values():
            urls.extend(_output_urls(item))
        return urls
    if isinstance(value, list):
        urls: list[str] = []
        for item in value:
            urls.extend(_output_urls(item))
        return urls
    return []


def poll_prediction(
    api_key: str,
    prediction_id: str,
    *,
    poll_interval: float,
    timeout: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> list[str]:
    started = clock()
    encoded_id = urllib.parse.quote(prediction_id, safe="")
    url = f"{API_BASE}/predictions/{encoded_id}/result"

    while clock() - started < timeout:
        response = _request_json("GET", url, api_key, attempts=3, sleep=sleep)
        data = _unwrap(response)
        status = str(data.get("status") or data.get("state") or "").lower()
        urls = _output_urls(data)

        if status in TERMINAL_SUCCESS or (not status and urls):
            if not urls:
                raise MuapiVideoError("Prediction completed without an output URL")
            return urls
        if status in TERMINAL_FAILURE:
            detail = data.get("error") or data.get("message") or "unknown error"
            raise MuapiVideoError(f"Prediction {status}: {_redact(str(detail), api_key)}")

        sleep(poll_interval)

    raise MuapiVideoError(f"Timed out after {timeout:g}s waiting for prediction")


def _validate_output_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise MuapiVideoError("MuAPI output URL must use HTTPS")
    if parsed.username or parsed.password:
        raise MuapiVideoError("MuAPI output URL must not contain user information")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise MuapiVideoError("MuAPI output URL must not target a private address")
    return parsed


def download_video(
    url: str,
    output_path: Path,
    *,
    attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    _validate_output_url(url)
    request = urllib.request.Request(
        url, headers={"User-Agent": "agi-super-team-muapi-video-gen/1.0"}
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                final_url = response.geturl() if hasattr(response, "geturl") else url
                _validate_output_url(final_url)
                content = response.read(MAX_VIDEO_BYTES + 1)
            if len(content) > MAX_VIDEO_BYTES:
                raise MuapiVideoError("Downloaded video exceeds the 512 MiB safety limit")
            if not content:
                raise MuapiVideoError("Downloaded video is empty")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)
            return
        except urllib.error.HTTPError as exc:
            if exc.code in TRANSIENT_HTTP_CODES and attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise MuapiVideoError(f"Video download failed with HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise MuapiVideoError(f"Video download failed: {exc}") from exc
    raise MuapiVideoError("Video download exhausted its attempts")


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    prompt = str(args.prompt).strip()
    if not prompt:
        raise MuapiVideoError("prompt must not be empty")
    if args.ratio not in ASPECT_RATIOS:
        raise MuapiVideoError(f"unsupported aspect ratio: {args.ratio}")
    if args.resolution not in RESOLUTIONS:
        raise MuapiVideoError(f"unsupported resolution: {args.resolution}")
    if not 5 <= args.duration <= 20:
        raise MuapiVideoError("duration must be between 5 and 20 seconds")
    return {
        "prompt": prompt,
        "aspect_ratio": args.ratio,
        "resolution": args.resolution,
        "duration": args.duration,
        "generate_audio": bool(args.generate_audio),
    }


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate one FLUX 3 video through MuAPI"
    )
    parser.add_argument("prompt", help="Text description of the video")
    parser.add_argument("-o", "--output", required=True, help="Output MP4 path")
    parser.add_argument("-r", "--ratio", choices=ASPECT_RATIOS, default="9:16")
    parser.add_argument("-d", "--duration", type=int, default=5)
    parser.add_argument("--resolution", choices=RESOLUTIONS, default="720p")
    parser.add_argument(
        "--generate-audio", action="store_true", help="Request synchronized audio"
    )
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--yes", action="store_true", help="Confirm one paid POST")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        if args.poll_interval <= 0 or args.timeout <= 0:
            raise MuapiVideoError("poll interval and timeout must be positive")
        payload = build_payload(args)
        output_path = Path(args.output).expanduser()
        plan = {
            "provider": "muapi",
            "endpoint": f"{API_BASE}/{ENDPOINT}",
            "payload": payload,
            "output": str(output_path),
            "billable_post_attempts": 1,
        }

        if not args.yes:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            print("Preview only. Re-run with --yes to send one paid request.", file=sys.stderr)
            return 2

        api_key = os.environ.get("MUAPI_API_KEY", "").strip()
        if not api_key:
            raise MuapiVideoError("MUAPI_API_KEY is required")

        prediction_id = submit_prediction(api_key, payload)
        output_urls = poll_prediction(
            api_key,
            prediction_id,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        download_video(output_urls[0], output_path)
        result = {
            "success": True,
            "prediction_id": prediction_id,
            "endpoint": ENDPOINT,
            "output": str(output_path),
        }
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(output_path)
        return 0
    except MuapiVideoError as exc:
        error = {"success": False, "error": str(exc)}
        if getattr(args, "json_output", False):
            print(json.dumps(error, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
