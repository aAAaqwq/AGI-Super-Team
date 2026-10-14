#!/usr/bin/env python3
"""Anonymous Pear Video downloader."""

from anonymous_ytdlp_downloader import PlatformConfig, run_cli  # noqa: E402


CONFIG = PlatformConfig(
    platform="pearvideo",
    display_name="Pear Video",
    hosts=("pearvideo.com",),
    extractor_keys=("PearVideo",),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(CONFIG))
