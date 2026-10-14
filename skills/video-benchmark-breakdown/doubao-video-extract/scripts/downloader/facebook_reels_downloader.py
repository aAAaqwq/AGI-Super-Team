#!/usr/bin/env python3
"""Downloader for public Facebook Reels."""

from __future__ import annotations

import re
from yt_dlp_candidate_common import PlatformSpec, run_cli  # noqa: E402


SPEC = PlatformSpec(
    platform="facebook_reels",
    display_name="Facebook Reels",
    description="Resolve or download a public Facebook Reel with anonymous yt-dlp.",
    url_pattern=re.compile(
        r"https?://(?:(?:www|m)\.)?facebook\.com/reel/\d+/?(?:[?#].*)?",
        re.IGNORECASE,
    ),
    input_help="Public facebook.com/reel/<id> URL or share text containing one.",
    solution=(
        "Use a public facebook.com/reel/<id> URL. Ordinary Facebook Video pages, "
        "private posts, deleted Reels, login-only content, and fb.watch short links "
        "are outside this candidate's current scope."
    ),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(SPEC))
