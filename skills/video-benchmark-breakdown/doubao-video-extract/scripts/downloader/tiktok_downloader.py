#!/usr/bin/env python3
"""Downloader for public TikTok videos."""

from __future__ import annotations

import re
from yt_dlp_candidate_common import PlatformSpec, run_cli  # noqa: E402


SPEC = PlatformSpec(
    platform="tiktok",
    display_name="TikTok",
    description="Resolve or download a public TikTok video with anonymous yt-dlp.",
    url_pattern=re.compile(
        r"https?://(?:www\.)?tiktok\.com/@[^/?#]+/video/\d+/?(?:[?#].*)?",
        re.IGNORECASE,
    ),
    input_help="Public tiktok.com/@user/video/<id> URL or share text containing one.",
    solution=(
        "Use a public full TikTok video URL. Ensure yt-dlp was installed with the "
        "default and curl-cffi extras so Chrome impersonation is available. Private, "
        "deleted, region-restricted, login-only, or IP-blocked videos are unsupported."
    ),
    default_impersonate="chrome",
)


if __name__ == "__main__":
    raise SystemExit(run_cli(SPEC))
