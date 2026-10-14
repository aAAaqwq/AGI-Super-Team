#!/usr/bin/env python3
"""Downloader for public Instagram Reels."""

from __future__ import annotations

import re
from yt_dlp_candidate_common import PlatformSpec, run_cli  # noqa: E402


SPEC = PlatformSpec(
    platform="instagram_reels",
    display_name="Instagram Reels",
    description="Resolve or download a public Instagram Reel with anonymous yt-dlp.",
    url_pattern=re.compile(
        r"https?://(?:www\.)?instagram\.com/reel/[^/?#]+/?(?:[?#].*)?",
        re.IGNORECASE,
    ),
    input_help="Public Instagram Reel URL or share text containing one.",
    solution=(
        "Use a public instagram.com/reel/<shortcode> URL. Private, deleted, "
        "age-restricted, login-only, or rate-limited Reels are unsupported."
    ),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(SPEC))
