#!/usr/bin/env python3
"""Downloader for public X video posts."""

from __future__ import annotations

import re

from yt_dlp_candidate_common import PlatformSpec, run_cli


SPEC = PlatformSpec(
    platform="x",
    display_name="X",
    description="Resolve or download a public X video post with anonymous yt-dlp.",
    url_pattern=re.compile(
        r"https?://(?:(?:www|mobile)\.)?(?:x\.com|twitter\.com)/"
        r"[^/?#]+/status/\d+(?:/video/\d+)?/?(?:[?#].*)?",
        re.IGNORECASE,
    ),
    input_help="Public x.com/<user>/status/<id> URL or share text containing one.",
    solution=(
        "Use a public X status URL containing video. Private, deleted, login-only, "
        "age-restricted, region-restricted, rate-limited, or non-video posts are unsupported."
    ),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(SPEC))
