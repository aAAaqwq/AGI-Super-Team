#!/usr/bin/env python3
"""Anonymous Tencent Video downloader."""

from anonymous_ytdlp_downloader import PlatformConfig, run_cli  # noqa: E402


CONFIG = PlatformConfig(
    platform="tencent_video",
    display_name="Tencent Video",
    hosts=("v.qq.com",),
    extractor_keys=("VQQVideo",),
    minimum_python=(3, 9),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(CONFIG))
