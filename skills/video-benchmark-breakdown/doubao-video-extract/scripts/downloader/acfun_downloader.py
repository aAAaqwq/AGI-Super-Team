#!/usr/bin/env python3
"""Anonymous AcFun downloader."""

from anonymous_ytdlp_downloader import PlatformConfig, run_cli  # noqa: E402


CONFIG = PlatformConfig(
    platform="acfun",
    display_name="AcFun",
    hosts=("acfun.cn",),
    extractor_keys=("AcFunVideo",),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(CONFIG))
