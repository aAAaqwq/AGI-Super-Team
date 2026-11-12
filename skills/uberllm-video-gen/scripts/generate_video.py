#!/usr/bin/env python3
"""Generate one UberLLM text-to-video clip with a single, confirmed POST."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable


API_BASE = "https://api.uberllm.dev/v1"
API_HOST = "api.uberllm.dev"
DEFAULT_MODEL = "fal-ai/veo3.1/lite"
USER_AGENT = "agi-super-team-uberllm-video-gen/1.0"
RUNNING = {"queued", "running"}
TERMINAL_FAILURE = {"failed", "canceled", "expired"}
TRANSIENT_HTTP_CODES = {408, 429, 500, 502, 503, 504}


class UberLLMVideoError(RuntimeError):
    """Raised when an UberLLM request cannot be completed safely."""


def _request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    *,
    attempts: int = 1,
    headers: dict[str, str] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            **(headers or {}),
        },
    )

    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                if not isinstance(result, dict):
                    raise UberLLMVideoError("UberLLM returned a non-object response")
                return result
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code in TRANSIENT_HTTP_CODES and attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise UberLLMVideoError(
                f"UberLLM {method} failed with HTTP {exc.code}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise UberLLMVideoError(f"UberLLM {method} request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise UberLLMVideoError("UberLLM returned invalid JSON") from exc

    raise UberLLMVideoError(f"UberLLM {method} request exhausted its attempts")


def quote_job(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    # "validate": true checks the request as if it were real; nothing is made or charged.
    return _request_json(
        "POST", f"{API_BASE}/video/generations", api_key, {**payload, "validate": True}
    )


def submit_job(api_key: str, payload: dict[str, Any]) -> str:
    # Billable generation submissions are intentionally never retried.
    response = _request_json(
        "POST",
        f"{API_BASE}/video/generations",
        api_key,
        payload,
        attempts=1,
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    job_id = response.get("id")
    if not job_id:
        raise UberLLMVideoError(
            "UberLLM accepted no identifiable job; do not resubmit automatically"
        )
    return str(job_id)


def poll_job(
    api_key: str,
    job_id: str,
    *,
    poll_interval: float,
    timeout: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    started = clock()
    url = f"{API_BASE}/video/generations/{urllib.parse.quote(job_id, safe='')}"

    while clock() - started < timeout:
        job = _request_json("GET", url, api_key, attempts=3, sleep=sleep)
        status = str(job.get("status", "")).lower()

        if status == "succeeded":
            urls = [
                item.get("url")
                for item in job.get("results") or []
                if isinstance(item, dict) and item.get("url")
            ]
            if not urls:
                raise UberLLMVideoError("Job succeeded without a result URL")
            return job
        if status in TERMINAL_FAILURE:
            error = job.get("error") or {}
            detail = error.get("message") if isinstance(error, dict) else error
            raise UberLLMVideoError(f"Job {status}: {detail or 'unknown error'}")
        if status not in RUNNING:
            raise UberLLMVideoError(f"Job returned unknown status {status!r}")

        sleep(poll_interval)

    raise UberLLMVideoError(
        f"Timed out after {timeout:g}s; job {job_id} keeps running and is billed when it ends"
    )


def download_video(
    url: str,
    output_path: Path,
    api_key: str,
    *,
    attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    headers = {"User-Agent": USER_AGENT}
    # Result links on api.uberllm.dev need the same key; never send it to any other host.
    if urllib.parse.urlsplit(url).hostname == API_HOST:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                content = response.read()
            if not content:
                raise UberLLMVideoError("Downloaded video is empty")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)
            return
        except urllib.error.HTTPError as exc:
            if exc.code in TRANSIENT_HTTP_CODES and attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise UberLLMVideoError(f"Video download failed with HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt + 1 < attempts:
                sleep(2**attempt)
                continue
            raise UberLLMVideoError(f"Video download failed: {exc}") from exc
    raise UberLLMVideoError("Video download exhausted its attempts")


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": args.model,
        "prompt": args.prompt,
        "aspect_ratio": args.ratio,
        "duration_seconds": args.duration,
        "resolution": args.resolution,
    }
    if args.max_cost is not None:
        if args.max_cost <= 0:
            raise UberLLMVideoError("--max-cost must be positive")
        payload["max_cost"] = args.max_cost
    return payload


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate one text-to-video clip through UberLLM"
    )
    parser.add_argument("prompt", help="Text description of the video")
    parser.add_argument("-o", "--output", required=True, help="Output MP4 path")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="UberLLM video model id")
    parser.add_argument("-r", "--ratio", default="16:9", help="Aspect ratio, e.g. 16:9 or 9:16")
    parser.add_argument("-d", "--duration", type=int, default=4, help="Clip length in seconds")
    parser.add_argument("--resolution", default="720p", help="e.g. 720p or 1080p")
    parser.add_argument("--max-cost", type=float, help="Most the job may be billed, in USD")
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument(
        "--quote", action="store_true", help="Ask UberLLM for the price; nothing is charged"
    )
    parser.add_argument("--yes", action="store_true", help="Confirm one paid POST")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def _api_key() -> str:
    api_key = os.environ.get("UBERLLM_API_KEY", "").strip()
    if not api_key:
        raise UberLLMVideoError("UBERLLM_API_KEY is required")
    return api_key


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        if args.poll_interval <= 0 or args.timeout <= 0:
            raise UberLLMVideoError("poll interval and timeout must be positive")
        payload = build_payload(args)

        if args.quote and not args.yes:
            quote = quote_job(_api_key(), payload)
            print(json.dumps(quote, ensure_ascii=False, indent=2))
            return 0 if quote.get("valid", True) else 1

        if not args.yes:
            plan = {
                "provider": "uberllm",
                "endpoint": f"{API_BASE}/video/generations",
                "payload": payload,
                "output": str(Path(args.output)),
                "billable_post_attempts": 1,
            }
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            print(
                "Preview only. Re-run with --quote to see the price (nothing is charged), "
                "or with --yes to send one paid request.",
                file=sys.stderr,
            )
            return 2

        api_key = _api_key()
        job_id = submit_job(api_key, payload)
        job = poll_job(
            api_key,
            job_id,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        output_path = Path(args.output).expanduser()
        download_video(job["results"][0]["url"], output_path, api_key)
        result = {
            "success": True,
            "job_id": job_id,
            "model": job.get("model") or args.model,
            "cost_usd": (job.get("usage") or {}).get("cost_usd"),
            "output": str(output_path),
        }
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(output_path)
        return 0
    except UberLLMVideoError as exc:
        error = {"success": False, "error": str(exc)}
        if getattr(args, "json_output", False):
            print(json.dumps(error, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
