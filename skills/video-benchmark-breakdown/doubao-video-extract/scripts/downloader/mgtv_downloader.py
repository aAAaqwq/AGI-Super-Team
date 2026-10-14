#!/usr/bin/env python3
"""Anonymous Mango TV downloader."""

from anonymous_ytdlp_downloader import PlatformConfig, run_cli  # noqa: E402


CONFIG = PlatformConfig(
    platform="mgtv",
    display_name="Mango TV",
    hosts=("mgtv.com",),
    extractor_keys=("MGTV", "MangoTV"),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(CONFIG))
