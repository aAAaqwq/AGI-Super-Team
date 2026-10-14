#!/usr/bin/env python3
"""Downloader for public Twitch Clips."""

from __future__ import annotations

import re
from yt_dlp_candidate_common import PlatformSpec, run_cli  # noqa: E402


SPEC = PlatformSpec(
    platform="twitch_clips",
    display_name="Twitch Clips",
    description="Resolve or download a public Twitch Clip with anonymous yt-dlp.",
    url_pattern=re.compile(
        r"https?://(?:(?:clips\.)twitch\.tv/[^/?#]+|"
        r"(?:www\.)?twitch\.tv/[^/?#]+/clip/[^/?#]+)/?(?:[?#].*)?",
        re.IGNORECASE,
    ),
    input_help="Public clips.twitch.tv URL, Twitch channel clip URL, or share text.",
    solution=(
        "Use a public Twitch Clip URL. This candidate does not support Twitch "
        "live streams, VODs, subscriber-only clips, deleted clips, or login-only content."
    ),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(SPEC))
