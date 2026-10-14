#!/usr/bin/env python3
"""Anonymous CCTV web video downloader."""

from anonymous_ytdlp_downloader import PlatformConfig, run_cli  # noqa: E402


CONFIG = PlatformConfig(
    platform="cctv",
    display_name="CCTV web video",
    hosts=("tv.cctv.com", "cntv.cn"),
    extractor_keys=("CCTV",),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(CONFIG))
